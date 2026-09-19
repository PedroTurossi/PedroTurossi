"""
Telemetry: GitHub data (GraphQL with a token, REST as a fallback) and the
komarev.com profile view counter. Any failure keeps the last values saved in
data/telemetry.json.

Languages are ranked by bytes of code across the user's own repositories
(forks excluded), exactly how GitHub's linguist measures them.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .fmt import fail, warn

LINGUIST = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "C#": "#178600",
    "C++": "#f34b7d", "C": "#555555", "Java": "#b07219", "PHP": "#4F5D95", "HTML": "#e34c26",
    "CSS": "#663399", "SCSS": "#c6538c", "Shell": "#89e051", "PowerShell": "#012456",
    "Batchfile": "#C1F12E", "Go": "#00ADD8", "Rust": "#dea584", "Lua": "#000080",
    "GDScript": "#355570", "ShaderLab": "#222c37", "HLSL": "#aace60", "GLSL": "#5686a5",
    "Kotlin": "#A97BFF", "Ruby": "#701516", "Dockerfile": "#384d54", "Assembly": "#6E4C13",
    "Jupyter Notebook": "#DA5B0B", "Vue": "#41b883", "Hack": "#878787", "Makefile": "#427819",
}

USER_AGENT = "terminal-readme"
TIMEOUT = 30

Q_PROFILE = """
query($login: String!, $cursor: String, $privacy: RepositoryPrivacy) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { contributionYears }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, privacy: $privacy) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 20, orderBy: { field: SIZE, direction: DESC }) {
          edges { size node { name color } }
        }
      }
    }
  }
}"""


def now_iso():
    moment = datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _request(url, token="", body=None, accept="application/vnd.github+json"):
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            return res.status, res.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", "replace")


def _via_graphql(cfg, token):
    def graphql(query, variables):
        status, text = _request("https://api.github.com/graphql", token, {"query": query, "variables": variables})
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {}
        if status != 200 or payload.get("errors"):
            messages = "; ".join(e.get("message", "") for e in payload.get("errors") or []) or f"HTTP {status}"
            raise RuntimeError(f"GraphQL: {messages}")
        return payload["data"]

    login = cfg["username"]
    privacy = None if cfg["languages"]["includePrivate"] else "PUBLIC"
    language_repos = []
    cursor = None
    while True:
        data = graphql(Q_PROFILE, {"login": login, "cursor": cursor, "privacy": privacy})
        user = data.get("user")
        if not user:
            raise RuntimeError(f'user "{login}" not found')
        for node in user["repositories"]["nodes"]:
            language_repos.append([{"name": e["node"]["name"], "color": e["node"]["color"], "bytes": e["size"]}
                                   for e in node["languages"]["edges"]])
        page = user["repositories"]["pageInfo"]
        cursor = page["endCursor"] if page["hasNextPage"] else None
        if not cursor:
            break

    commits = 0
    years = user["contributionsCollection"]["contributionYears"]
    if years:
        fields = "\n".join(
            f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") '
            "{ totalCommitContributions restrictedContributionsCount }" for y in years)
        data = graphql(f"query($login: String!) {{ user(login: $login) {{ {fields} }} }}", {"login": login})
        for year in data["user"].values():
            commits += year["totalCommitContributions"]
            if cfg["stats"]["countPrivateContributions"]:
                commits += year["restrictedContributionsCount"]

    return {"repos": user["repositories"]["totalCount"], "followers": user["followers"]["totalCount"],
            "commits": commits, "languageRepos": language_repos}


def _via_rest(cfg, token=""):
    if not token:
        warn("no token: using the public REST API (approximate commits, 60 requests/h limit).")

    def rest(path):
        status, text = _request(f"https://api.github.com{path}", token)
        if status != 200:
            try:
                detail = json.loads(text).get("message", "")
            except (json.JSONDecodeError, AttributeError):
                detail = ""
            raise RuntimeError(f"GET {path}: HTTP {status}" + (f" ({detail})" if detail else ""))
        return json.loads(text)

    login = urllib.parse.quote(cfg["username"], safe="")
    profile = rest(f"/users/{login}")
    repos = []
    page = 1
    while True:
        batch = rest(f"/users/{login}/repos?per_page=100&type=owner&page={page}")
        repos += [r for r in batch if not r.get("fork")]
        if len(batch) < 100:
            break
        page += 1
    language_repos = []
    for repo in repos:
        langs = rest(f'/repos/{repo["full_name"]}/languages')
        language_repos.append([{"name": name, "bytes": size, "color": None} for name, size in langs.items()])
    try:
        commits = rest(f"/search/commits?q=author:{login}&per_page=1").get("total_count")
    except (RuntimeError, json.JSONDecodeError):
        commits = None
    return {"repos": len(repos), "followers": profile.get("followers"), "commits": commits, "languageRepos": language_repos}


def _read_view_counter(username):
    """Reads the komarev.com counter. Every read adds 1, so we keep track of how many we made."""
    status, svg = _request(f"https://komarev.com/ghpvc/?username={urllib.parse.quote(username, safe='')}", accept="image/svg+xml,*/*")
    if status != 200:
        raise RuntimeError(f"komarev: HTTP {status}")
    numbers = [re.sub(r"\D", "", m) for m in re.findall(r"<text[^>]*>\s*(\d[\d.,\s]*)\s*</text>", svg)]
    numbers = [n for n in numbers if n]
    if not numbers:
        raise RuntimeError("komarev: counter not found in the response")
    return int(numbers[-1])


def summarize_languages(language_repos, cfg):
    """Adds up bytes per language. Keeps only the top `languages.count`; percentages use the full total."""
    excluded = {l.lower() for l in cfg["languages"]["exclude"]}
    totals = {}
    for repo in language_repos:
        for lang in repo:
            name = lang["name"]
            if name.lower() in excluded:
                continue
            entry = totals.get(name)
            if entry is None:
                entry = {"name": name, "color": lang.get("color") or LINGUIST.get(name), "bytes": 0}
                totals[name] = entry
            entry["bytes"] += lang["bytes"]
    ranked = sorted(totals.values(), key=lambda l: -l["bytes"])
    total = sum(l["bytes"] for l in ranked) or 1
    top = ranked[:cfg["languages"]["count"]]
    return {"languageCount": len(ranked), "languages": [{**l, "percent": (l["bytes"] / total) * 100} for l in top]}


def collect(cfg, prev, token, wants_views):
    state = {
        "version": 1,
        "username": cfg["username"],
        "updatedAt": now_iso(),
        "repos": (prev or {}).get("repos", 0),
        "languageCount": (prev or {}).get("languageCount", 0),
        "languages": (prev or {}).get("languages", []),
        "stats": {"commits": None, "followers": None, "views": None, **((prev or {}).get("stats") or {})},
        "viewCounterSelfHits": (prev or {}).get("viewCounterSelfHits", 0),
    }
    if prev and prev.get("username") and prev["username"].lower() != cfg["username"].lower():
        warn(f'data/telemetry.json belongs to "{prev["username"]}"; starting fresh for "{cfg["username"]}".')
        state.update(repos=0, languageCount=0, languages=[], viewCounterSelfHits=0,
                     stats={"commits": None, "followers": None, "views": None})
        prev = None

    fresh = None
    errors = []
    if token:
        try:
            fresh = _via_graphql(cfg, token)
        except (RuntimeError, OSError, KeyError, TypeError) as err:
            errors.append(str(err))
            warn(f"GraphQL failed ({err}); trying the REST API.")
    if fresh is None:
        try:
            fresh = _via_rest(cfg, token)
        except (RuntimeError, OSError, KeyError, TypeError, json.JSONDecodeError) as err:
            errors.append(str(err))

    if fresh is not None:
        state["repos"] = fresh["repos"]
        state.update(summarize_languages(fresh["languageRepos"], cfg))
        for stat in ("followers", "commits"):
            if fresh[stat] is not None:  # the REST fallback cannot always count commits
                state["stats"][stat] = fresh[stat]
    elif not prev:
        fail(f'could not collect data: {"; ".join(errors)}')
    else:
        warn(f'failed to collect data ({"; ".join(errors)}); keeping the previous values.')

    if wants_views:
        try:
            raw = _read_view_counter(cfg["username"])
            state["viewCounterSelfHits"] += 1
            state["stats"]["views"] = max(0, raw - state["viewCounterSelfHits"])
        except (RuntimeError, OSError) as err:
            warn(f"failed to read profile views ({err}); keeping the previous value.")

    return state


def demo_state(cfg):
    language_repos = [[
        {"name": "Python", "bytes": 184000}, {"name": "PHP", "bytes": 121000}, {"name": "C#", "bytes": 96000},
        {"name": "Java", "bytes": 52000}, {"name": "JavaScript", "bytes": 31000}, {"name": "Shell", "bytes": 12000},
        {"name": "CSS", "bytes": 9000},
    ]]
    return {"version": 1, "username": cfg["username"], "updatedAt": now_iso(), "repos": 15,
            **summarize_languages(language_repos, cfg),
            "stats": {"commits": 412, "followers": 6, "views": 238}, "viewCounterSelfHits": 0}
