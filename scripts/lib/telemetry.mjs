/**
 * Telemetry: GitHub (GraphQL with a token, REST without one) and the komarev view counter.
 * Any failure keeps the last values saved in data/telemetry.json.
 */
import { warn, fail } from './log.mjs';

const LINGUIST = {
  Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#3178c6', 'C#': '#178600',
  'C++': '#f34b7d', C: '#555555', Java: '#b07219', PHP: '#4F5D95', HTML: '#e34c26',
  CSS: '#663399', SCSS: '#c6538c', Shell: '#89e051', PowerShell: '#012456',
  Batchfile: '#C1F12E', Go: '#00ADD8', Rust: '#dea584', Lua: '#000080',
  GDScript: '#355570', ShaderLab: '#222c37', HLSL: '#aace60', GLSL: '#5686a5',
  Kotlin: '#A97BFF', Ruby: '#701516', Dockerfile: '#384d54', Assembly: '#6E4C13',
  'Jupyter Notebook': '#DA5B0B', Vue: '#41b883', Hack: '#878787', Makefile: '#427819',
};

function headers(token) {
  return {
    'User-Agent': 'terminal-readme',
    Accept: 'application/vnd.github+json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

const Q_PROFILE = `
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
}`;

async function viaGraphQL(cfg, token) {
  const graphql = async (query, variables) => {
    const res = await fetch('https://api.github.com/graphql', {
      method: 'POST',
      headers: { ...headers(token), 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, variables }),
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok || json.errors) {
      throw new Error(`GraphQL: ${json.errors?.map((e) => e.message).join('; ') || `HTTP ${res.status}`}`);
    }
    return json.data;
  };

  const login = cfg.username;
  const privacy = cfg.languages.includePrivate ? null : 'PUBLIC';
  const languageRepos = [];
  let cursor = null;
  let user;
  do {
    const data = await graphql(Q_PROFILE, { login, cursor, privacy });
    if (!data.user) throw new Error(`user "${login}" not found`);
    user = data.user;
    for (const node of user.repositories.nodes) {
      languageRepos.push(node.languages.edges.map((e) => ({ name: e.node.name, color: e.node.color, bytes: e.size })));
    }
    cursor = user.repositories.pageInfo.hasNextPage ? user.repositories.pageInfo.endCursor : null;
  } while (cursor);

  let commits = 0;
  const years = user.contributionsCollection.contributionYears;
  if (years.length) {
    const fields = years
      .map((y) => `y${y}: contributionsCollection(from: "${y}-01-01T00:00:00Z", to: "${y}-12-31T23:59:59Z") { totalCommitContributions restrictedContributionsCount }`)
      .join('\n');
    const data = await graphql(`query($login: String!) { user(login: $login) { ${fields} } }`, { login });
    for (const year of Object.values(data.user)) {
      commits += year.totalCommitContributions;
      if (cfg.stats.countPrivateContributions) commits += year.restrictedContributionsCount;
    }
  }

  return { repos: user.repositories.totalCount, followers: user.followers.totalCount, commits, languageRepos };
}

async function viaREST(cfg) {
  warn('no token: using the public REST API (approximate commits, 60 requests/h limit).');
  const rest = async (path) => {
    const res = await fetch(`https://api.github.com${path}`, { headers: headers('') });
    if (!res.ok) throw new Error(`GET ${path}: HTTP ${res.status}`);
    return res.json();
  };
  const login = encodeURIComponent(cfg.username);
  const profile = await rest(`/users/${login}`);
  const list = (await rest(`/users/${login}/repos?per_page=100&type=owner`)).filter((r) => !r.fork);
  const languageRepos = [];
  for (const repo of list) {
    const langs = await rest(`/repos/${repo.full_name}/languages`);
    languageRepos.push(Object.entries(langs).map(([name, bytes]) => ({ name, bytes, color: null })));
  }
  const search = await rest(`/search/commits?q=author:${login}&per_page=1`).catch(() => ({ total_count: null }));
  return { repos: list.length, followers: profile.followers, commits: search.total_count, languageRepos };
}

/** Reads the komarev.com counter. Every read adds 1, so we keep track of how many we made. */
async function readViewCounter(username) {
  const res = await fetch(`https://komarev.com/ghpvc/?username=${encodeURIComponent(username)}`, {
    headers: { 'User-Agent': 'terminal-readme' },
  });
  if (!res.ok) throw new Error(`komarev: HTTP ${res.status}`);
  const svg = await res.text();
  const numbers = [...svg.matchAll(/<text[^>]*>\s*([\d][\d.,\s]*)\s*<\/text>/g)]
    .map((m) => m[1].replace(/\D/g, ''))
    .filter(Boolean);
  if (!numbers.length) throw new Error('komarev: counter not found in the response');
  return Number(numbers.at(-1));
}

export function summarizeLanguages(languageRepos, cfg) {
  const excluded = new Set(cfg.languages.exclude.map((l) => String(l).toLowerCase()));
  const totals = new Map();
  for (const repo of languageRepos) {
    for (const { name, color, bytes } of repo) {
      if (excluded.has(name.toLowerCase())) continue;
      const entry = totals.get(name) ?? { name, color: color ?? LINGUIST[name] ?? null, bytes: 0 };
      entry.bytes += bytes;
      totals.set(name, entry);
    }
  }
  const all = [...totals.values()].sort((a, b) => b.bytes - a.bytes);
  const sum = all.reduce((acc, l) => acc + l.bytes, 0) || 1;
  return { languageCount: all.length, languages: all.map((l) => ({ ...l, percent: (l.bytes / sum) * 100 })) };
}

export async function collect(cfg, prev, { mode, token, wantsViews }) {
  if (mode === 'demo') return demoState(cfg);
  if (mode === 'offline') {
    if (!prev) fail('--offline needs data/telemetry.json. Run once without the flag.');
    return prev;
  }

  const state = {
    version: 1,
    username: cfg.username,
    updatedAt: new Date().toISOString(),
    repos: prev?.repos ?? 0,
    languageCount: prev?.languageCount ?? 0,
    languages: prev?.languages ?? [],
    stats: { commits: null, followers: null, views: null, ...prev?.stats },
    viewCounterSelfHits: prev?.viewCounterSelfHits ?? 0,
  };

  try {
    const fresh = token ? await viaGraphQL(cfg, token) : await viaREST(cfg);
    Object.assign(state, { repos: fresh.repos, ...summarizeLanguages(fresh.languageRepos, cfg) });
    state.stats.followers = fresh.followers;
    state.stats.commits = fresh.commits;
  } catch (err) {
    if (!prev) fail(`could not collect data: ${err.message}`);
    warn(`failed to collect data (${err.message}); keeping the previous values.`);
  }

  if (wantsViews) {
    try {
      const raw = await readViewCounter(cfg.username);
      state.viewCounterSelfHits += 1;
      state.stats.views = Math.max(0, raw - state.viewCounterSelfHits);
    } catch (err) {
      warn(`failed to read profile views (${err.message}); keeping the previous value.`);
    }
  }

  return state;
}

function demoState(cfg) {
  const languageRepos = [[
    { name: 'Python', bytes: 184000 }, { name: 'PHP', bytes: 121000 }, { name: 'C#', bytes: 96000 },
    { name: 'Java', bytes: 52000 }, { name: 'JavaScript', bytes: 31000 }, { name: 'Shell', bytes: 12000 },
    { name: 'CSS', bytes: 9000 },
  ]];
  return {
    version: 1, username: cfg.username, updatedAt: new Date().toISOString(), repos: 15,
    ...summarizeLanguages(languageRepos, cfg),
    stats: { commits: 412, followers: 6, views: 238 }, viewCounterSelfHits: 0,
  };
}
