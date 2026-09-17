/** Fixed interface strings. `en` is the default; `pt-BR` is kept as an option. */
export const STRINGS = {
  en: {
    system: '{host}-os 2.0 (tty1)',
    boot: [
      'Loading kernel modules',
      'Mounting /home/{user}',
      'Connecting to api.github.com',
      'Indexing {repos} repositories',
      'Detecting {languageCount} languages',
      'Syncing telemetry',
    ],
    session: 'Starting session',
    labels: {
      name: 'Name', description: 'Bio', focus: 'Focus', repos: 'Repos', commits: 'Commits',
      followers: 'Followers', views: 'Views', languages: 'Languages',
    },
    tmux: { repos: 'repos', windows: ['boot', 'neofetch', 'projects'] },
    apps: {
      rhythm: { score: 'SCORE', combo: 'COMBO', hit: 'PERFECT!' },
      pipeline: {
        headers: ['ORDER', 'STAGE', 'PROGRESS'],
        stages: ['closing', 'checking', 'packing', 'shipping'],
        log: [
          ['OP-0917 closed', '40 volumes'],
          ['OP-0918 checking', 'batch B'],
          ['OP-0919 packing', '17 of 40'],
          ['OP-0916 shipped', 'NF 00481'],
        ],
        volumes: 'volumes',
        rate: '12/h',
      },
      homelab: {
        command: 'lab status',
        headers: ['SERVICE', 'STATE', 'CPU', 'MEM'],
        states: { up: 'up', idle: 'idle', scan: 'scan' },
        scan: 'nmap -sV 10.0.0.0/24 --open',
      },
      open: { mkdir: 'mkdir -p ~/projects/next && cd $_', file: 'idea.md', heading: 'next project' },
    },
    meta: { stack: 'stack', url: 'url' },
    emptyFocus: 'add your focus areas in config.json',
    emptyLanguages: 'no languages found',
  },
  'pt-BR': {
    system: '{host}-os 2.0 (tty1)',
    boot: [
      'Carregando módulos do kernel',
      'Montando /home/{user}',
      'Conectando a api.github.com',
      'Indexando {repos} repositórios',
      'Detectando {languageCount} linguagens',
      'Sincronizando telemetria',
    ],
    session: 'Iniciando sessão',
    labels: {
      name: 'Nome', description: 'Bio', focus: 'Foco', repos: 'Repos', commits: 'Commits',
      followers: 'Seguidores', views: 'Visualizações', languages: 'Linguagens',
    },
    tmux: { repos: 'repos', windows: ['boot', 'neofetch', 'projects'] },
    apps: {
      rhythm: { score: 'SCORE', combo: 'COMBO', hit: 'PERFECT!' },
      pipeline: {
        headers: ['ORDEM', 'ETAPA', 'PROGRESSO'],
        stages: ['fechamento', 'conferência', 'embalagem', 'expedição'],
        log: [
          ['OP-0917 fechada', '40 volumes'],
          ['OP-0918 em conferência', 'lote B'],
          ['OP-0919 embalando', '17 de 40'],
          ['OP-0916 expedida', 'NF 00481'],
        ],
        volumes: 'volumes',
        rate: '12/h',
      },
      homelab: {
        command: 'lab status',
        headers: ['SERVIÇO', 'ESTADO', 'CPU', 'MEM'],
        states: { up: 'ativo', idle: 'ocioso', scan: 'scan' },
        scan: 'nmap -sV 10.0.0.0/24 --open',
      },
      open: { mkdir: 'mkdir -p ~/projects/proximo && cd $_', file: 'ideia.md', heading: 'próximo projeto' },
    },
    meta: { stack: 'stack', url: 'url' },
    emptyFocus: 'adicione suas áreas de foco em config.json',
    emptyLanguages: 'nenhuma linguagem encontrada',
  },
};
