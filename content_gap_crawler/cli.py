"""Command line entry point: `content-gap-crawler YOUR_SITE COMPETITOR [COMPETITOR ...]`."""
from pathlib import Path

import click

from . import __version__, core
from .benchmark import STAT
from .report import Report, write_excel


@click.command()
@click.argument("your_site")
@click.argument("competitors", nargs=-1, required=True)
@click.option("--max-urls", default=5000, show_default=True, help="Max URLs read per site.")
@click.option("--min-pages", default=3, show_default=True,
              help="A phrase becomes a topic when at least this many URLs (all sites) use it.")
@click.option("--delay", default=0.5, show_default=True, help="Seconds between sitemap downloads.")
@click.option("-o", "--output", default="content_gap", show_default=True,
              help="Report name; writes <name>.html and <name>.xlsx")
@click.version_option(__version__)
def main(your_site, competitors, max_urls, min_pages, delay, output):
    """Compare topic coverage of YOUR_SITE with COMPETITORS.

    Each site can be a domain (sitemaps found via robots.txt), a sitemap URL,
    or a local sitemap .xml / .xml.gz / .txt URL list.

    Built by Meer Hamza - linkedin.com/in/meerhamza-seo
    """
    urls_by_site, me = {}, None
    for i, source in enumerate((your_site, *competitors)):
        urls = core.load_site(source, max_urls, delay)
        label = core.site_label(source, urls)
        click.echo(f"{label}: {len(urls)} URLs")
        if not urls:
            raise click.ClickException(f"no URLs found for {source}")
        urls_by_site[label] = urls
        me = me or label

    pages = core.assign_topics(urls_by_site, min_pages)
    cov = core.coverage(pages, me)
    missing = cov[cov["status"] == "missing"]
    thin = cov[cov["status"] == "thin"]
    counts = cov["status"].value_counts()

    report = Report(title="Content gap report", subtitle=f"{me} vs {', '.join(list(urls_by_site)[1:])}",
                    tool="content-gap-crawler")
    report.add_cards([
        ("Topics found", len(cov)),
        ("Missing topics", int(counts.get("missing", 0)), "bad"),
        ("Thin topics", int(counts.get("thin", 0)), "warn"),
        ("Untapped topics", int(counts.get("untapped", 0)), "warn"),
        ("Topics you lead", int(counts.get("leading", 0)), "good"),
    ])
    report.add_benchmark(STAT, how_used="Gaps are measured per topic, not per keyword: how many pages each site "
                                        "has on a theme. Close missing and thin topics with clusters of linked "
                                        "pages, not one-off posts.")
    report.add_table("Missing topics", missing, note="2+ competitors cover the topic, you have no page.",
                     sheet="Missing")
    report.add_table("Thin topics", thin, note="You have pages, but fewer than half the competitor average.",
                     sheet="Thin")
    report.add_table("Competitor pages to study", core.example_urls(pages, missing["topic"].tolist()
                                                                    + thin["topic"].tolist(), me),
                     sheet="Pages to study")
    report.add_table("Full topic coverage", cov, sheet="Coverage")
    report.add_table("All URLs with topic", pages, sheet="All URLs")

    html_path = report.save_html(Path(output).with_suffix(".html"))
    xlsx_path = write_excel(report.sheets, Path(output).with_suffix(".xlsx"))
    click.secho(f"Report: {html_path}\nData:   {xlsx_path}", fg="green", bold=True)
    click.echo(cov.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
