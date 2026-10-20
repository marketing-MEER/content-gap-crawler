import functools
import gzip
import http.server
import tempfile
import threading
import unittest
from pathlib import Path

from click.testing import CliRunner

from content_gap_crawler import cli, core

EXAMPLES = Path(__file__).parent.parent / "examples"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class TopicTest(unittest.TestCase):
    def test_slug_words_drop_folders_years_stopwords_and_utility_pages(self):
        self.assertEqual(core.slug_words("https://x.com/blog/2024/the-best-sales-pipeline-guide-2025/"),
                         ["sales", "pipeline"])
        self.assertEqual(core.slug_words("https://x.com/pricing"), [])
        self.assertEqual(core.slug_words("https://x.com/"), [])

    def test_normaliser_only_folds_into_existing_forms(self):
        norm = core.normaliser({"template", "templates", "forecast", "forecasting", "sales"})
        self.assertEqual(norm("templates"), "template")
        self.assertEqual(norm("forecasting"), "forecast")
        self.assertEqual(norm("sales"), "sales")  # "sale" never appears, so keep "sales"

    def test_assign_and_coverage(self):
        urls = {
            "me.com": ["https://me.com/blog/crm-migration-plan", "https://me.com/blog/crm-migration-tips",
                       "https://me.com/blog/lead-scoring-model"],
            "a.com": [f"https://a.com/lead-scoring-{w}" for w in ["model", "examples2", "b2b", "tools"]]
                     + ["https://a.com/email-template-cold", "https://a.com/email-templates-follow-up"],
            "b.com": ["https://b.com/lead-scoring-basics", "https://b.com/email-template-sales",
                      "https://b.com/crm-migration-checklist"],
        }
        pages = core.assign_topics(urls, min_pages=3)
        cov = core.coverage(pages, "me.com").set_index("topic")
        self.assertEqual(cov.at["email template", "status"], "missing")    # a + b cover it, me none
        self.assertEqual(cov.at["lead scoring", "status"], "thin")         # 1 vs avg 2.5
        self.assertEqual(cov.at["crm migration", "status"], "leading")
        self.assertEqual(cov.at["lead scoring", "pages_to_match_leader"], 3)


class SitemapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        handler = functools.partial(QuietHandler, directory=str(root))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        base = f"http://127.0.0.1:{cls.server.server_port}"
        (root / "robots.txt").write_text(f"User-agent: *\nSitemap: {base}/sitemap_index.xml\n")
        (root / "sitemap_index.xml").write_text(
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<sitemap><loc>{base}/posts.xml.gz</loc></sitemap></sitemapindex>")
        (root / "posts.xml.gz").write_bytes(gzip.compress(
            ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
             f"<url><loc>{base}/blog/a</loc></url><url><loc>{base}/blog/b</loc></url></urlset>").encode()))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = base

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def test_robots_index_and_gzip(self):
        urls = core.load_site(self.base, delay=0)
        self.assertEqual(urls, [f"{self.base}/blog/a", f"{self.base}/blog/b"])

    def test_local_file(self):
        urls = core.load_site(str(EXAMPLES / "brightcrm_sitemap.xml"))
        self.assertTrue(urls and all(u.startswith("https://brightcrm.io/") for u in urls))


class CliTest(unittest.TestCase):
    def test_example_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gap"
            args = [str(EXAMPLES / f) for f in ["brightcrm_sitemap.xml", "pipelinehq_sitemap.xml",
                                                 "salesdeck_sitemap.xml"]] + ["-o", str(out)]
            res = CliRunner().invoke(cli.main, args)
            self.assertEqual(res.exit_code, 0, res.output)
            html = out.with_suffix(".html").read_text(encoding="utf-8")
            self.assertIn("lead scoring", html)
            self.assertTrue(out.with_suffix(".xlsx").exists())


if __name__ == "__main__":
    unittest.main()
