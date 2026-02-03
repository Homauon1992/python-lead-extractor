import csv
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook

EMAIL_REGEX = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)

SOCIAL_PATTERNS = {
    "LinkedIn": re.compile(r"^https?://(www\.)?linkedin\.com/.*", re.IGNORECASE),
    "Twitter": re.compile(
        r"^https?://(www\.)?(twitter\.com|x\.com)/.*", re.IGNORECASE
    ),
    "Instagram": re.compile(r"^https?://(www\.)?instagram\.com/.*", re.IGNORECASE),
    "Facebook": re.compile(r"^https?://(www\.)?facebook\.com/.*", re.IGNORECASE),
}


def normalize_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if not raw_url:
        return ""
    if not urlparse(raw_url).scheme:
        return f"https://{raw_url}"
    return raw_url


def extract_emails(soup: BeautifulSoup) -> set[str]:
    emails = set(EMAIL_REGEX.findall(soup.get_text(" ", strip=True)))
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if href.lower().startswith("mailto:"):
            mail = href.split(":", 1)[1].split("?", 1)[0].strip()
            if mail:
                emails.add(mail)
    return emails


def extract_social_links(soup: BeautifulSoup, base_url: str) -> dict[str, set[str]]:
    results: dict[str, set[str]] = {key: set() for key in SOCIAL_PATTERNS}
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not href:
            continue
        full_url = urljoin(base_url, href)
        for platform, pattern in SOCIAL_PATTERNS.items():
            if pattern.match(full_url):
                results[platform].add(full_url)
    return results


def write_csv(
    output_path: Path,
    emails: set[str],
    social_links: dict[str, set[str]],
) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["type", "value"])
        for email in sorted(emails):
            writer.writerow(["Email", email])
        for platform, links in social_links.items():
            for link in sorted(links):
                writer.writerow([platform, link])


def write_excel(
    output_path: Path,
    emails: set[str],
    social_links: dict[str, set[str]],
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Leads"
    sheet.append(["type", "value"])
    for email in sorted(emails):
        sheet.append(["Email", email])
    for platform, links in social_links.items():
        for link in sorted(links):
            sheet.append([platform, link])
    workbook.save(output_path)


def main() -> None:
    raw_url = input("Enter URL: ").strip()
    url = normalize_url(raw_url)
    if not url:
        print("No URL provided.")
        return

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Failed to fetch URL: {exc}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    emails = extract_emails(soup)
    social_links = extract_social_links(soup, url)

    csv_path = Path("leads.csv")
    xlsx_path = Path("leads.xlsx")
    write_csv(csv_path, emails, social_links)
    write_excel(xlsx_path, emails, social_links)
    total_social = sum(len(v) for v in social_links.values())
    print(
        f"Saved {len(emails)} emails and {total_social} social links to {csv_path} and {xlsx_path}."
    )


if __name__ == "__main__":
    main()
