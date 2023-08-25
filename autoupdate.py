#!/usr/bin/python
import json
import re
import requests
import time
from datetime import datetime
import os
import mdtoc


def get_github_token():
	if os.environ.get('GITHUB_ACCESS_TOKEN'):
		return os.environ['GITHUB_ACCESS_TOKEN']
	try:
		with open(os.path.join(os.environ['HOME'], '.github_access_token')) as f:
			token = f.read()
			return token.strip()
	except Exception as e:
		print(e)
		return None


def get_crawlers():
	try:
		with open("crawlers.json") as f:
			data = json.load(f)
			return data
	except Exception as e:
		print(e)
		return None


def save_crawlers(data):
	try:
		with open("crawlers.json", "w") as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
	except Exception as e:
		print(e)


def export_readme(data):
	if data is None:
		return
	languages = {}
	keys = sorted(data, key=lambda x: (-data[x].get('stargazers_count', 0), data[x].get('name')))
	for k in keys:
		c = data[k]
		language = c.get('language')
		if not language:
			continue
		if language not in languages:
			languages[language] = []
		languages[language].append(c)
	title = "Awesome-crawlers ![Awesome](https://cdn.jsdelivr.net/gh/sindresorhus/awesome@d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg)"
	description = "A collection of awesome web crawler, spider and resources in different languages."
	readme = []
	readme.append(f"# {title}\n\n")
	readme.append(f"{description}\n\n")
	readme.append(f"**Update date: {datetime.now().strftime('%Y-%m-%d')}**\n\n")
	readme.append("## Contents\n\n")
	contents = []
	# All
	contents.append(f"## All\n")
	contents.append(f"\n")
	contents.append(f"| name | stars | language | update date | description |\n")
	contents.append(f"| ---- | ----- | -------- | ----------- | ----------- |\n")
	for k in keys:
		c = data[k]
		name = c.get('name', '')
		url = c.get('url', '')
		stars = c.get('stargazers_count', '--')
		language = c.get('language', '--')
		updated_at = c.get('updated_at', '--')
		updated_at = updated_at[:10]
		description = c.get('description', '--')
		description = description.replace("\n", "<br/>")
		contents.append(f"| [{name}]({url}) | {stars} | {language} | {updated_at} | {description} |\n")
	contents.append(f"\n")
	# Languages
	for k in sorted(languages):
		contents.append(f"## {k}\n")
		contents.append(f"\n")
		contents.append(f"| name | stars | update date | description |\n")
		contents.append(f"| ---- | ----- | ----------- | ----------- |\n")
		crawlers = languages[k]
		for c in crawlers:
			name = c.get('name', '')
			url = c.get('url', '')
			stars = c.get('stargazers_count', '--')
			updated_at = c.get('updated_at', '--')
			updated_at = updated_at[:10]
			description = c.get('description', '--')
			description = description.replace("\n", "<br/>")
			contents.append(f"| [{name}]({url}) | {stars} | {updated_at} | {description} |\n")
		contents.append(f"\n")
	toc = mdtoc.generate_toc(contents, start_level=2, end_level=2)
	readme.append(f"{toc}\n\n")
	readme += contents
	with open("README.md", "w") as f:
		f.writelines(readme)
	print(f"export README.md success")


def get_github_repo_info(url, token=None, retry=True):
	m = re.match(r"https?://github\.com/([^/]+)/([^/\.]+).*", url)
	if not m:
		return None
	username = m.group(1)
	repo = m.group(2)
	api = f"https://api.github.com/repos/{username}/{repo}"
	headers = {}
	if token:
		headers["Authorization"] = f"Bearer {token}"
	res = requests.get(api, headers=headers)
	x_ratelimit_remaining = -1
	x_ratelimit_reset = -1
	x_ratelimit_limit = -1
	x_ratelimit_used = -1
	if res and res.headers:
		x_ratelimit_remaining = res.headers.get('X-RateLimit-Remaining')
		x_ratelimit_reset = res.headers.get('X-RateLimit-Reset')
		x_ratelimit_limit = res.headers.get('X-RateLimit-Limit')
		x_ratelimit_used = res.headers.get('X-RateLimit-Used')
	print(f"get: {api}, res: {res}, ratelimit: {x_ratelimit_limit}, remaining: {x_ratelimit_remaining}")
	if res and res.status_code != 200 and res.headers and retry:
		if x_ratelimit_remaining == 0 and x_ratelimit_reset > 0:
			current_time = time.time()
			left_reset_time = ceil(x_ratelimit_reset - current_time)
			while left_reset_time > 0:
				print(f"max rate limit, wait reset: {left_reset_time}s")
				time.sleep(1)
				left_reset_time -= 1
			return get_github_repo_info(url, token=token, retry=False)
	if not res:
		return None, None
	if res.status_code != 200:
		return None, res.status_code
	return res.json(), res.status_code


def update_crawlers(force=False):
	data = get_crawlers()
	if data is None:
		return
	token = get_github_token()
	update_keys = [
		"name",
		"description",
		"homepage",
		"language",
		"stargazers_count",
		"watchers_count",
		"forks_count",
		"archived",
		"open_issues",
		"created_at",
		"updated_at",
		"disabled"
	]
	current_time = int(time.time() * 1000)
	one_hour_time = 60 * 60 * 1000
	for k, v in data.items():
		url = v.get("url")
		if not url or "github.com" not in url:
			continue
		if v.get('not_exists'):
			print(f"{k}: {url} not exists")
			continue
		update_time = v.get('update_time', 0)
		if not force and update_time > 0 and abs(update_time - current_time) < 12 * one_hour_time:
			update_time = datetime.fromtimestamp(update_time/1000).strftime('%Y-%m-%d %H:%M:%S')
			print(f"{k}: {url}, update: updated at {update_time}")
			continue
		info, status_code = get_github_repo_info(url, token=token)
		if not info:
			if status_code == 404:
				v['not_exists'] = True
			continue
		updated = False
		for uk in update_keys:
			uv = info.get(uk)
			if uv and uv != '':
				v[k] = uv
				updated = True
		if updated:
			v['update_time'] = int(time.time() * 1000)
			data[k] = v
			print(f"{k}: {url}, update: success")
		else:
			print(f"{k}: {url}, update: same")
	save_crawlers(data)
	export_readme(data)


if __name__ == '__main__':
	update_crawlers()

