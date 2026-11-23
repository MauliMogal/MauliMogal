"""Rewrites the open source stats in README.md from the GitHub search API.

Counts pull requests by USER to repositories owned by ORG, and lists the merged ones.
Runs daily from .github/workflows/stats.yml. Only reads public data.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter

USER = "MauliMogal"
ORG = "frappe"
README = os.path.join(os.path.dirname(__file__), "..", "README.md")
START, END = "<!-- stats:start -->", "<!-- stats:end -->"


def search(query: str) -> list[dict]:
	items, page = [], 1
	while True:
		url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
			{"q": query, "per_page": 100, "page": page, "sort": "created", "order": "desc"}
		)
		req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
		if token := os.environ.get("GITHUB_TOKEN"):
			req.add_header("Authorization", f"Bearer {token}")
		with urllib.request.urlopen(req) as resp:
			data = json.load(resp)
		items += data["items"]
		if len(items) >= data["total_count"] or not data["items"]:
			return items
		page += 1


def repo_of(pr: dict) -> str:
	return pr["repository_url"].split("/repos/")[1]


def render(prs: list[dict]) -> str:
	merged = [p for p in prs if p.get("pull_request", {}).get("merged_at")]
	open_ = [p for p in prs if p["state"] == "open"]
	repos = sorted({repo_of(p) for p in merged})
	per_repo = Counter(repo_of(p) for p in merged)

	lines = [
		"| Merged PRs | Open PRs | Frappe repos contributed to |",
		"|:-:|:-:|:-:|",
		f"| **{len(merged)}** | {len(open_)} | {len(repos)} |",
		"",
	]
	if merged:
		lines.append("**Merged**")
		lines.append("")
		for p in merged:
			date = p["pull_request"]["merged_at"][:10]
			lines.append(f"- [{repo_of(p)}#{p['number']}]({p['html_url']}): {p['title']} ({date})")
		lines.append("")
	if open_:
		lines.append("**In review**")
		lines.append("")
		for p in open_:
			lines.append(f"- [{repo_of(p)}#{p['number']}]({p['html_url']}): {p['title']}")
		lines.append("")
	if per_repo:
		lines.append("Merged by repo: " + ", ".join(f"{r} ({n})" for r, n in per_repo.most_common()))
		lines.append("")
	lines.append(
		f"<sub>Updated daily from GitHub. [See all my PRs](https://github.com/pulls?q=is%3Apr+author%3A{USER}+org%3A{ORG})</sub>"
	)
	return "\n".join(lines)


def main():
	prs = search(f"author:{USER} type:pr org:{ORG}")
	with open(README) as f:
		readme = f.read()
	block = f"{START}\n{render(prs)}\n{END}"
	updated = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, readme, flags=re.S)
	if updated != readme:
		with open(README, "w") as f:
			f.write(updated)
		print("README updated")
	else:
		print("No change")


if __name__ == "__main__":
	main()
