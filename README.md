<div align="center">

# 🗺️ content-gap-crawler

### See which topics your competitors cover in depth and you don't, straight from their sitemaps.

[![tests](https://github.com/marketing-MEER/content-gap-crawler/actions/workflows/ci.yml/badge.svg)](https://github.com/marketing-MEER/content-gap-crawler/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![No API keys](https://img.shields.io/badge/API%20keys-none%20needed-brightgreen)
[![Part of SEO Toolbox](https://img.shields.io/badge/part%20of-SEO%20Toolbox-orange)](https://github.com/marketing-MEER/seo-toolbox)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Meer%20Hamza-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)

[🚀 Quick start](#quick-start) · [⚙️ How it works](#how-it-works) · [📄 Report](#report) · [❓ FAQ](#faq) · [👤 Author](#author)

</div>

---

## 💡 What it does

Keyword tools show the keywords you're missing. They don't show the **topics** where a competitor has built ten linked pages and you have one, and that depth is what tends to hold rankings.

`content-gap-crawler` reads the XML sitemaps of your site and your competitors, turns every URL into a topic, and compares how many pages each site has per topic. It downloads only the sitemap files, never the pages, so it's fast and light on the sites.

- ✅ Finds sitemaps automatically from `robots.txt`, and follows sitemap indexes and `.gz` files
- ✅ Topics come from URL slugs, with no keyword tool or API needed
- ✅ Every topic is labelled **missing**, **thin**, **untapped**, **covered** or **leading**
- ✅ Lists the competitor pages to study for each gap

## 📊 Why this matters

> **Topic-Focused SEO Performs Better in Tough Markets** · NP Digital, October 2025 (50 sites, 25 per group, over 4 years)
> - 2023: Topic +18.7%, Keyword +2.5%.
> - 2024: Topic -3.3%, Keyword -18.1%.
> - 2025: Topic -12.7%, Keyword -21.6%.
> - Topic-focused content outperformed in all four years.
>
> Data: [Neil Patel marketing stats](https://neilpatel.com/marketing-stats/keyword-vs-topic-seo-performance/)

**How content-gap-crawler uses this:** the study's advice is to *"switch from keyword-first to topic-first content planning"* and *"cluster related content around core themes."* So the gap is measured per topic, as the number of pages each site has on a theme. A topic is **thin** when you have fewer than half the competitor average, and the report shows how many pages you'd need to match the deepest competitor.

<a id="quick-start"></a>

## 🚀 Quick start

```bash
git clone https://github.com/marketing-MEER/content-gap-crawler.git
cd content-gap-crawler
pip install -e .

# try it on the sample sitemaps
content-gap-crawler examples/brightcrm_sitemap.xml examples/pipelinehq_sitemap.xml examples/salesdeck_sitemap.xml

# real sites: just the domains (sitemaps are found via robots.txt)
content-gap-crawler yoursite.com competitor-one.com competitor-two.com
```

The first site is **you**. This writes **`content_gap.html`** (a formatted report) and **`content_gap.xlsx`** (all data).

> [!TIP]
> If the `content-gap-crawler` command isn't found, use `python -m content_gap_crawler`.

## 📥 Input

Each site can be given as:

| Input | Example | What happens |
|---|---|---|
| A domain | `competitor.com` | Reads `robots.txt` for `Sitemap:` lines, or falls back to `/sitemap.xml` |
| A sitemap URL | `https://site.com/post-sitemap.xml` | Reads it, following sitemap indexes and `.gz` files |
| A local file | `sitemap.xml`, `sitemap.xml.gz`, `urls.txt` | Reads the file (`.txt` = one URL per line, e.g. a Screaming Frog export) |

<a id="how-it-works"></a>

## ⚙️ How it works

1. **Collect URLs** from each site's sitemaps (up to `--max-urls`, with a pause between downloads).
2. **Read the slug**: only the last part of the path counts, so `/blog/2024/the-best-sales-pipeline-guide/` → `sales pipeline`.
   - Removed: years, numbers, filler words ("best", "guide", "how", "tips"…).
   - Skipped: utility pages like `/pricing`, `/contact`, `/about`.
3. **Merge word forms** only when both forms really occur in the URLs: `templates` → `template` and `forecasting` → `forecast`, while `sales` stays `sales`.
4. **Pick a topic** for every URL: its most widely used two-word phrase (used by at least `--min-pages` URLs across all sites), otherwise its most widely used single word.
5. **Compare** page counts per topic and label each one:

| Status | Rule |
|---|---|
| 🔴 **missing** | You have 0 pages; 2+ competitors cover it |
| 🟠 **thin** | You have fewer than half the competitor average |
| 🟡 **untapped** | You have 0 pages; 1 competitor covers it |
| ⚪ **covered** | You're between thin and the leader |
| 🟢 **leading** | You have at least as many pages as any competitor |

### Options

| Option | Default | What it does |
|---|---|---|
| `--max-urls` | `5000` | Max URLs read per site |
| `--min-pages` | `3` | A phrase becomes a topic when at least this many URLs (all sites) use it |
| `--delay` | `0.5` | Seconds between sitemap downloads |
| `-o`, `--output` | `content_gap` | Report name; writes `.html` and `.xlsx` |

<a id="report"></a>

## 📄 The report

| Section / Excel sheet | Shows |
|---|---|
| Summary cards | Topics found; missing, thin and untapped topics; topics you lead |
| **Missing** / **Thin** | Pages per site, competitors covering, competitor average and maximum, pages needed to match the leader |
| **Pages to study** | Up to 3 competitor URLs for each missing or thin topic |
| **Coverage** | Every topic and its status |
| **All URLs** | Every URL with its site and topic, to check or regroup by hand |

<details>
<summary>📄 Example: real output from <code>examples/</code> (fictional CRM sites)</summary>

| topic | brightcrm.io (you) | pipelinehq.com | salesdeck.io | status | pages to match leader |
|---|---|---|---|---|---|
| lead scoring | 0 | 4 | 5 | missing | 5 |
| customer retention | 0 | 2 | 4 | missing | 4 |
| sales pipeline | 2 | 8 | 5 | thin | 6 |
| email template | 1 | 5 | 4 | thin | 4 |
| sales forecast | 0 | 3 | 0 | untapped | 3 |
| crm integration | 2 | 3 | 0 | covered | 1 |
| contact management | 3 | 0 | 1 | leading | 0 |
| crm migration | 4 | 0 | 2 | leading | 0 |

</details>

## 🧰 More free SEO tools

This repo is one tool in the **[SEO Toolbox](https://github.com/marketing-MEER/seo-toolbox)**, a family of free, single-purpose SEO tools. Related:
- [keyword-gap-analyzer](https://github.com/marketing-MEER/keyword-gap-analyzer): the keyword-level view of the same question
- **topic-cluster-planner**: turn a gap topic into a pillar + spoke plan
- [seo-workhorse](https://github.com/marketing-MEER/seo-workhorse): audit, clustering, redirects and GSC quick wins in one CLI

<a id="faq"></a>

## ❓ FAQ

<details><summary><b>What if a site has no sitemap, or URLs like <code>/p?id=123</code>?</b></summary>

Topics come from URL slugs, so sites with ID-style URLs can't be read this way. Export their URLs with titles from a crawler and pass a `.txt` list. For those sites, a crawl-based tool such as competitor-onpage-benchmark fits better.
</details>

<details><summary><b>Why are some topics just one word?</b></summary>

When no two-word phrase is shared by enough URLs, the most common single word is used. Lower `--min-pages` to 2 for small sites, or raise it for big ones to get broader topics.
</details>

<details><summary><b>Does page count really mean depth?</b></summary>

It's a good proxy, not proof: one great page can beat five weak ones. Use the "Pages to study" sheet to check what the competitor pages actually cover.
</details>

<details><summary><b>Is my data sent anywhere?</b></summary>

No. It only downloads `robots.txt` and sitemap files from the sites you list, with its own user agent, and writes the report on your computer.
</details>

## 🧪 Tests

```bash
python -m unittest discover -s tests -t . -v
```

## 📄 License

[MIT](LICENSE). Free for personal and commercial use. Benchmark figures © their original publishers, quoted with a link to the source.

<a id="author"></a>

## 👤 Author

**Meer Hamza** · SEO Team Lead · Berlin 🇩🇪
10+ years in SEO, AEO and GEO. I build small tools that take the spreadsheet work out of SEO.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)
[![Email](https://img.shields.io/badge/Email-meerhamza5%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:meerhamza5@gmail.com)

<div align="center">

**If this saved you time, a ⭐ helps other SEOs find it.**

</div>
