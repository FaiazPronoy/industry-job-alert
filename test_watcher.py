import unittest
from datetime import date, datetime, timedelta, timezone

import watcher as w

NOW = datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc)  # Monday 10:00 Dhaka
DAY = timedelta(days=1)
PAGE = "https://example.com.bd/careers"


def page(*rows):
    body = "".join(f'<tr><td><a href="/job/{i}">{title}</a></td><td>{f"Deadline: {deadline}" if deadline else ""}</td></tr>'
                   for i, (title, deadline) in enumerate(rows))
    return f"<html><body><nav><a href='/x'>Internet Banking</a></nav><table>{body}</table></body></html>"


CONFIG = {"organisations": [
    {"name": "Example Bank", "sector": "Bank", "monitor_urls": [PAGE], "urls": [PAGE], "status": "Ready"},
    {"name": "Blocked Soft", "sector": "Software", "monitor_urls": [], "urls": ["https://blocked.example/jobs"],
     "status": "Manual", "note": "site bot check dekhay"}], "backup_sources": []}


class FakeFetcher:
    def __init__(self, html):
        self.html = html

    def __call__(self, sources):
        if self.html is None:
            return {s["url"]: w.FetchResult(s["url"], False, "timeout") for s in sources}
        return {s["url"]: w.FetchResult(s["url"], True, "ok", self.html, s["url"]) for s in sources}


class FailingNotifier:
    def send(self, text, silent=False):
        raise w.TelegramError("down")


class Silent:
    def __init__(self):
        self.messages, self.silent, self.deleted = [], [], []

    def send(self, text, silent=False):
        self.messages.append(text)
        self.silent.append(silent)
        return [id(text)]

    def delete(self, ids):
        self.deleted += ids


class Dates(unittest.TestCase):
    def test_formats(self):
        for text in ["Deadline: 25/11/2026", "Application deadline : 2026-11-25", "Last date: 25 Nov 2026",
                     "apply by November 25, 2026", "শেষ তারিখ: ২৫/১১/২০২৬", "on or before 25th November, 2026",
                     "Applicants must apply to www.example.com by the 25 November, 2026."]:
            self.assertEqual(w.find_deadline(text), date(2026, 11, 25), text)

    def test_posted_date_is_not_deadline(self):
        self.assertIsNone(w.find_deadline("Published 19/11/2026"))


class Filters(unittest.TestCase):
    def test_tech_posts(self):
        for title in ["Software Engineer (Backend)", "Junior Python Developer", "SQA Engineer", "Machine Learning Engineer",
                      "AI Engineer - LLM", "Data Analyst", "IT Officer", "Trainee Software Engineer", "DevOps Engineer",
                      "Software Engineering Intern"]:
            self.assertEqual(w.role_of(title), "Tech", title)

    def test_business_posts(self):
        for title in ["Management Trainee Officer (MTO)", "Probationary Officer", "Trainee Cash Officer", "Senior Officer",
                      "Executive, Marketing", "Relationship Manager - SME", "Assistant Manager, HR", "Supply Chain Analyst",
                      "Finance Intern", "Sales Engineer"]:
            self.assertEqual(w.role_of(title), "Business", title)

    def test_dropped_posts(self):
        for title in ["Head of Engineering", "Chief Risk Officer", "Senior Manager, Treasury", "General Manager",
                      "Executive, Production", "Electrical Engineer", "Medical Officer", "Driver", "Tech Lead (Java)",
                      "Software Architect", "Internet Banking", "Sustainable Finance", "Unclaimed & Inoperative Accounts",
                      "Life at Example", "Engineer", "Executive Committee", "Project Manager – FinTech",
                      "Principal Software Engineer", "Regional Manager - SEA FMIS", "AI Assistant -Coming Soon",
                      "Data & Business Administration Level 3 Apprenticeship - UK and Ireland", "Cloud & Engineering",
                      "Assistant Laboratory Analyst / Assistant QA Technician", "Junior Officer, Quality Control",
                      "Notice Regarding Appointment Letter Collection for Probationary Officer (PO)", "MTO List",
                      "Information Officer", "Key Executives", "Associate Scientist (Analytical Research & Development)"]:
            self.assertFalse(w.wanted_post(title, title) and w.classify(title, title, PAGE), title)

    def test_intern_tag(self):
        self.assertTrue(w.is_intern("Digitalyst Internship Program"))
        self.assertTrue(w.is_intern("Finance Intern"))
        self.assertFalse(w.is_intern("Internal Audit Officer"))

    def test_circular_text_says_which_board(self):
        self.assertEqual(w.circular_facts("Recruitment of Senior Officer and Officer (IT/Software)")["groups"], ["tech", "business"])
        self.assertEqual(w.circular_facts("Recruitment of Trainee Officer")["groups"], ["business"])

    def test_menu_words_are_not_posts(self):
        for title in ["Careers", "Job Openings", "Internships", "Apply Now"]:
            self.assertIsNone(w.classify(title, title, PAGE), title)


class Extraction(unittest.TestCase):
    def test_generic_link_uses_card_title(self):
        html = ("<main><div class='card'><h3>Software Engineer</h3><p>Application Deadline : 29/11/2026</p>"
                "<a href='/apply/1'>Apply Link</a><a href='/detail/1'>Detail information</a></div></main>")
        item = w.extract_items("X", html, PAGE)[0]
        self.assertIn("Software Engineer", item.title)
        self.assertEqual(item.deadline, date(2026, 11, 29))

    def test_session_parameter_does_not_change_key(self):
        a = w.Item("U", "Officer", "https://a.com/job?id=1&gsessionid=abc", PAGE, "")
        b = w.Item("U", "Officer", "https://a.com/job?id=1&gsessionid=xyz", PAGE, "")
        self.assertEqual(w.item_key(a), w.item_key(b))

    def test_web_app_job_routes_stay_separate(self):
        html = ('<div><a href="#/jobs/1">Junior Software Engineer</a><p>30 November 2026 8 Days Remaining</p></div>'
                '<div><a href="#/jobs/2">Data Analyst</a><p>24 November 2026 2 Days Remaining</p></div>')
        items = w.extract_items("U", html, "https://career.example.com/#/jobs")
        self.assertEqual(sorted(i.title for i in items), ["Data Analyst", "Junior Software Engineer"])


class Flow(unittest.TestCase):
    def go(self, html, now=NOW, config=CONFIG, fetcher=None):
        self.notifier = Silent()
        w.run(config, self.state, fetcher or FakeFetcher(html), self.notifier, now)
        return self.notifier.messages

    def setUp(self):
        self.state = w.new_state()

    def test_two_boards_every_hour(self):
        html = page(("Software Engineer", ""), ("Probationary Officer", "30/11/2026"), ("Head of IT", ""),
                    ("Old Trainee Officer", "01/01/2025"))
        for _ in range(2):
            tech, business = self.go(html)
            self.assertIn("SOFTWARE", tech)
            self.assertIn("Software Engineer", tech)
            self.assertNotIn("Probationary Officer", tech)
            self.assertIn("Probationary Officer", business)
            self.assertIn("BANK &amp; FINANCE", business)
            self.assertIn("[Bank]", business)
            self.assertNotIn("Head of IT", tech + business)
            self.assertNotIn("Old Trainee", business)
            self.assertNotIn("Internet Banking", tech + business)

    def test_existing_posts_are_listed_but_not_new(self):
        tech = self.go(page(("Software Engineer", "")))[0]
        self.assertIn("Software Engineer", tech)
        self.assertNotIn("NEW</b>", tech)

    def test_new_tag_only_on_publish_day(self):
        self.go(page(("Software Engineer", "")))
        html = page(("Software Engineer", ""), ("Data Analyst", "05/12/2026"))
        tech = self.go(html, NOW + timedelta(hours=1))[0]
        self.assertIn('NEW</b> · <b>Example Bank</b> [Bank] — <a href="https://example.com.bd/job/1">Data Analyst', tech)
        self.assertEqual(tech.count("NEW</b> ·"), 1)
        self.assertEqual(self.notifier.silent, [False, False])
        self.assertNotIn("NEW</b> ·", self.go(html, NOW + DAY)[0])

    def test_internship_section_and_tag(self):
        self.go(page(("Software Engineer", "")))
        tech = self.go(page(("Software Engineer", ""), ("Software Engineering Intern", "")))[0]
        self.assertIn("🎓 <b>INTERNSHIP</b> (1)", tech)
        self.assertIn("🎓 <b>Example Bank", tech)
        self.assertIn("1 ta internship", tech)

    def test_deadline_first_and_expired_hidden(self):
        html = page(("Officer, Marketing", "20/12/2026"), ("Trainee Officer", "25/11/2026"), ("Executive, Finance", ""))
        business = self.go(html)[1]
        self.assertLess(business.index("Trainee Officer"), business.index("Officer, Marketing"))
        self.assertLess(business.index("Officer, Marketing"), business.index("Executive, Finance"))
        self.assertNotIn("Trainee Officer", self.go(html, NOW + 3 * DAY)[1])

    def test_post_removed_from_page_disappears(self):
        self.go(page(("Software Engineer", ""), ("Data Analyst", "")))
        later = page(("Software Engineer", ""))
        self.go(later, NOW + DAY)
        self.assertNotIn("Data Analyst", self.go(later, NOW + 3 * DAY)[0])

    def test_previous_boards_are_deleted_and_quiet_when_nothing_new(self):
        html = page(("Software Engineer", ""))
        self.go(html)
        first = list(self.state["board_messages"])
        self.go(html)
        self.assertEqual(self.notifier.deleted, first)
        self.assertEqual(self.notifier.silent, [True, True])

    def test_failed_telegram_is_loud_next_run(self):
        self.go(page(("Software Engineer", "")))
        html = page(("Software Engineer", ""), ("IT Officer", ""))
        with self.assertRaises(w.TelegramError):
            w.run(CONFIG, self.state, FakeFetcher(html), FailingNotifier(), NOW)
        self.assertIn("IT Officer", self.go(html)[0])
        self.assertEqual(self.notifier.silent, [False, False])

    def test_bank_pdf_circular_lands_on_both_boards(self):
        class Pdf(FakeFetcher):
            def detail_info(self, urls):
                return {u: w.circular_facts("Recruitment of Officer (General) and Officer (IT/Software). "
                                            "Apply by 30 November 2026") for u in urls}
        html = "<main><table><tr><td><a href='/c/recruitment-2026.pdf'>Recruitment Circular 2026</a></td></tr></table></main>"
        tech, business = self.go(html, fetcher=Pdf(html))
        self.assertIn("Recruitment Circular 2026", tech)
        self.assertIn("Recruitment Circular 2026", business)
        self.assertIn("30 Nov", tech)

    def test_broken_source_is_listed(self):
        self.go(page(("Software Engineer", "")))
        for _ in range(w.FAILS_BEFORE_ALERT):
            business = self.go(None)[1]
        self.assertIn("check kora jachhe na", business)

    def test_sunday_weekly_manual_list(self):
        business = self.go(page(("Software Engineer", "")), NOW - DAY)[1]
        self.assertIn("Blocked Soft", business)
        self.assertIn("site bot check dekhay", business)
        self.assertNotIn("Weekly manual", self.go(page(("Software Engineer", "")), NOW - DAY + timedelta(hours=1))[1])

    def test_many_posts_collapse(self):
        rows = [(f"Software Engineer {i}", "") for i in range(w.SHOWN_UNDATED + 5)]
        tech = self.go(page(*rows))[0]
        self.assertIn("Aro 5 ta post", tech)
        for part in w.split_message(tech):
            self.assertEqual(part.count("<blockquote"), part.count("</blockquote>"))
            self.assertLessEqual(len(part), 3900)


class TelegramFormat(unittest.TestCase):
    def test_title_is_escaped(self):
        record = {"org": "A&B", "title": "<Officer>", "category": "Business", "deadline": "2026-11-30",
                  "url": "https://a.com/?a=1&b=2", "first_seen": "2026-11-01", "level": "strong"}
        line = w.board_line(record, date(2026, 11, 23), {"A&B": "Bank"})
        self.assertIn("A&amp;B", line)
        self.assertIn("&lt;Officer&gt;", line)
        self.assertIn("a=1&amp;b=2", line)

    def test_split(self):
        parts = w.split_message("\n".join(["x" * 100] * 100))
        self.assertTrue(all(len(p) <= 3900 for p in parts))


if __name__ == "__main__":
    unittest.main()
