'use strict';

const state = {
  dashboard: null,
  deliveries: [],
  events: [],
  operations: { pacotes: [], respostas: [] },
  executions: { execucoes: [], executor: {} },
};

const actionLabels = {
  gerar_imagem: 'Gerar imagem',
  revisar_e_aprovar_imagem: 'Revisar e aprovar imagem',
  gerar_video: 'Gerar vídeo',
  gerar_carrossel: 'Gerar carrossel',
  verificar_tentativa_interrompida: 'Verificar tentativa interrompida',
  corrigir_estado_invalido: 'Corrigir estado inválido',
  corrigir_plano_pendente: 'Corrigir plano pendente',
  concluido: 'Concluído',
  desconhecida: 'Ação não identificada',
};

const statusLabels = {
  aprovada: 'Aprovada',
  rejeitada: 'Rejeitada',
  aguardando_aprovacao: 'Aguardando aprovação',
  nao_necessaria: 'Não necessária',
  nao_necessario: 'Não necessário',
  nao_solicitado: 'Não solicitado',
  gerada: 'Gerada',
  gerado: 'Gerado',
  pendente: 'Pendente',
  pronto: 'Pronto',
  queued: 'Na fila local',
  running: 'Em execução',
  succeeded: 'Concluída',
  failed: 'Falhou',
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(Number(value || 0));
}

function formatDate(value) {
  if (!value) return 'Horário não registrado';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date);
}

function humanize(value) {
  if (!value) return 'Não informado';
  return statusLabels[value] || actionLabels[value] || String(value).replaceAll('_', ' ');
}

function chip(text, tone = '') {
  return el('span', `chip ${tone ? `is-${tone}` : ''}`.trim(), text);
}

function emptyState(message) {
  return el('div', 'empty-state', message);
}

function mediaPreview(media, className = 'media-preview', label = 'mídia') {
  const wrapper = el('div', className);
  if (!media || !media.url || !media.valido) {
    wrapper.append(el('span', '', `Sem prévia disponível para ${label}`));
    return wrapper;
  }
  const extension = String(media.extensao || '').toLowerCase();
  if (['.mp4', '.mov', '.webm', '.mkv'].includes(extension)) {
    const video = el('video');
    video.src = media.url;
    video.controls = true;
    video.preload = 'metadata';
    video.setAttribute('aria-label', `Prévia em vídeo de ${label}`);
    wrapper.append(video);
  } else {
    const image = el('img');
    image.src = media.url;
    image.alt = `Prévia de ${label}`;
    image.loading = 'lazy';
    wrapper.append(image);
  }
  return wrapper;
}

function setConnection(kind, message) {
  const status = document.querySelector('#connection-status');
  status.className = `connection ${kind ? `is-${kind}` : ''}`.trim();
  status.textContent = message;
}

function announce(message) {
  document.querySelector('#live-region').textContent = message;
}

function setView(id, updateLocation = true, focusHeading = false) {
  const target = document.getElementById(id);
  if (!target?.classList.contains('view')) return;
  document.querySelectorAll('.view').forEach((section) => {
    const active = section.id === id;
    section.classList.toggle('is-active', active);
    section.hidden = !active;
  });
  document.querySelectorAll('.nav-tab').forEach((button) => {
    const active = button.dataset.view === id;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
    if (active) {
      if (button === document.activeElement) {
        button.scrollIntoView({ behavior: 'auto', block: 'nearest', inline: 'nearest' });
      }
    } else {
      button.removeAttribute('aria-current');
    }
  });
  const heading = document.querySelector(`#${id} h1`);
  if (heading && focusHeading) {
    heading.setAttribute('tabindex', '-1');
    heading.focus({ preventScroll: true });
  }
  if (updateLocation) history.replaceState(null, '', `#${id}`);
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function renderKpis() {
  const summary = state.dashboard.resumo;
  const actions = state.dashboard.proximas_acoes;
  const values = [
    ['Produções', summary.producoes, 'Revisões ativas consideradas'],
    ['Clipes', summary.clipes, 'Na revisão ativa'],
    ['Aguardam revisão', actions.revisar_e_aprovar_imagem || 0, 'Decisão humana necessária', 'attention'],
    ['Entregas', summary.entregas, 'Arquivos no índice local'],
    ['Diagnósticos', summary.erros, 'Pontos para conferir', summary.erros ? 'alert' : ''],
  ];
  const grid = document.querySelector('#kpi-grid');
  grid.replaceChildren();
  values.forEach(([label, value, help, tone]) => {
    const card = el('article', `kpi ${tone ? `is-${tone}` : ''}`.trim());
    card.append(
      el('span', 'kpi-value', formatNumber(value)),
      el('span', 'kpi-label', label),
      el('span', 'kpi-help', help),
    );
    grid.append(card);
  });
}

function renderActions() {
  const entries = Object.entries(state.dashboard.proximas_acoes)
    .sort((left, right) => right[1] - left[1]);
  const root = document.querySelector('#action-bars');
  root.replaceChildren();
  if (!entries.length) {
    root.append(emptyState('Nenhuma próxima ação identificada.'));
    return;
  }
  const maximum = Math.max(...entries.map((entry) => entry[1]), 1);
  entries.forEach(([key, value]) => {
    const row = el('div', 'bar-row');
    const label = el('span', 'bar-label', humanize(key));
    const track = el('div', 'bar-track');
    track.setAttribute('aria-hidden', 'true');
    const fill = el('div', 'bar-fill');
    fill.style.width = `${Math.max((value / maximum) * 100, 1)}%`;
    track.append(fill);
    row.append(label, track, el('span', 'bar-value', formatNumber(value)));
    root.append(row);
  });
}

function renderDiagnostics() {
  const root = document.querySelector('#diagnostics-list');
  root.replaceChildren();
  const diagnostics = state.dashboard.erros || [];
  if (!diagnostics.length) {
    root.append(emptyState('Nenhum diagnóstico de integridade no recorte atual.'));
    return;
  }
  diagnostics.forEach((item) => {
    const box = el('div', 'diagnostic');
    const origin = item.linha ? `${item.origem} · linha ${item.linha}` : item.origem;
    box.append(el('strong', '', origin || 'Diagnóstico'), el('span', '', item.erro));
    root.append(box);
  });
}

function eventNode(event) {
  const row = el('article', 'event');
  row.append(
    el('time', 'event-time', formatDate(event.timestamp || event.inicio_em || event.inicio)),
    el('strong', '', event.id_clipe || event.producao_id || 'Evento do pipeline'),
    chip(humanize(event.etapa), 'info'),
    el('span', 'event-detail', event.erro || humanize(event.resultado)),
  );
  return row;
}

function renderEvents(target, events, limit) {
  const root = document.querySelector(target);
  root.replaceChildren();
  const selected = [...events].reverse().slice(0, limit || events.length);
  if (!selected.length) {
    root.append(emptyState('Ainda não há eventos estruturados para mostrar.'));
    return;
  }
  selected.forEach((event) => root.append(eventNode(event)));
}

function clipMatches(clip, production, filters) {
  const text = `${production.id} ${clip.id} ${clip.produto_id || ''}`.toLocaleLowerCase('pt-BR');
  return (!filters.search || text.includes(filters.search))
    && (!filters.production || production.id === filters.production)
    && (!filters.action || clip.proxima_acao === filters.action);
}

function renderClip(clip) {
  const card = el('article', 'clip-card');
  card.append(mediaPreview(clip.imagem, 'media-preview', `imagem do clipe ${clip.id}`));
  const body = el('div');
  const title = el('div', 'clip-title');
  title.append(el('h3', '', clip.id), el('span', 'clip-order', `Ordem ${clip.ordem || '—'}`));
  const chips = el('div', 'chip-row');
  chips.append(
    chip(humanize(clip.papel), 'info'),
    chip(humanize(clip.imagem_status), clip.imagem ? 'success' : 'warning'),
    chip(humanize(clip.video_status), clip.video ? 'success' : 'warning'),
  );
  if (clip.aprovacao_vinculada) chips.append(chip('Aprovação vinculada', 'success'));
  if (clip.lock_ativo) chips.append(chip('Em execução', 'info'));
  body.append(title, el('p', 'production-meta', clip.produto_id || 'Produto não informado'), chips);
  (clip.erros || []).forEach((error) => body.append(el('p', 'clip-error', error)));
  const action = el('div', 'next-action');
  action.append(el('small', '', 'Próxima ação'), el('strong', '', humanize(clip.proxima_acao)));
  card.append(body, action);
  return card;
}

function populateFilters() {
  const productions = state.dashboard.producoes || [];
  const productionSelect = document.querySelector('#production-filter');
  const actionSelect = document.querySelector('#action-filter');
  productionSelect.replaceChildren(new Option('Todas', ''));
  actionSelect.replaceChildren(new Option('Todas', ''));
  [...new Set(productions.map((item) => item.id))].sort().forEach((id) => {
    productionSelect.append(new Option(id, id));
  });
  Object.keys(state.dashboard.proximas_acoes).sort().forEach((action) => {
    actionSelect.append(new Option(humanize(action), action));
  });
}

function renderProductions() {
  const filters = {
    search: document.querySelector('#search-input').value.trim().toLocaleLowerCase('pt-BR'),
    production: document.querySelector('#production-filter').value,
    action: document.querySelector('#action-filter').value,
  };
  const root = document.querySelector('#production-list');
  root.replaceChildren();
  let clipCount = 0;
  let productionCount = 0;
  state.dashboard.producoes.forEach((production) => {
    const clips = production.clipes.filter((clip) => clipMatches(clip, production, filters));
    if (!clips.length) return;
    productionCount += 1;
    clipCount += clips.length;
    const details = el('details', 'production');
    if (productionCount === 1) details.open = true;
    const summary = el('summary');
    const title = el('div', 'production-title');
    title.append(el('h2', '', production.id), chip(`${clips.length} clipes`, 'info'));
    summary.append(title, el('span', 'production-meta', `Revisão ${production.revisao}`));
    const list = el('div', 'clip-list');
    clips.forEach((clip) => list.append(renderClip(clip)));
    details.append(summary, list);
    root.append(details);
  });
  document.querySelector('#production-result-count').textContent =
    `${formatNumber(productionCount)} produções · ${formatNumber(clipCount)} clipes exibidos`;
  if (!productionCount) root.append(emptyState('Nenhum clipe corresponde aos filtros atuais.'));
}

function reviewCard(production, clip) {
  const form = el('form', 'review-card');
  form.append(mediaPreview(
    clip.imagem,
    'media-preview review-preview',
    'frame do clipe ' + clip.id,
  ));

  const body = el('div', 'review-body');
  const heading = el('div', 'review-heading');
  const title = el('div');
  title.append(
    el('h2', '', clip.id),
    el('p', 'review-meta', production.id + ' · revisão ' + production.revisao),
  );
  const decision = clip.decisao_humana || '';
  const tone = decision === 'aprovada' && clip.aprovacao_vinculada
    ? 'success'
    : decision === 'rejeitada' ? 'error' : 'warning';
  heading.append(title, chip(decision ? humanize(decision) : 'Sem decisão', tone));

  const details = el(
    'p',
    'review-meta',
    (clip.produto_id || 'Produto não informado') + ' · ' + humanize(clip.papel),
  );
  const hash = el(
    'p',
    'review-hash',
    'SHA-256: ' + clip.imagem.sha256 + ' · revisão: ' + production.revisao,
  );
  body.append(heading, details, hash);

  if (clip.ultima_revisao_imagem?.justificativa) {
    body.append(el(
      'p',
      'review-reason',
      'Última justificativa: ' + clip.ultima_revisao_imagem.justificativa,
    ));
  }

  const reasonLabel = el('label');
  reasonLabel.append(el('span', '', 'Justificativa para rejeição'));
  const reason = el('textarea');
  reason.name = 'reason';
  reason.maxLength = 500;
  reason.placeholder = 'Descreva objetivamente o que precisa ser corrigido.';
  reasonLabel.append(reason);

  const confirmation = el('label', 'confirm-field');
  const checkbox = el('input');
  checkbox.type = 'checkbox';
  checkbox.name = 'confirm';
  checkbox.required = true;
  confirmation.append(
    checkbox,
    el('span', '', 'Confirmo que revisei este frame e esta revisão.'),
  );

  const actions = el('div', 'review-actions');
  const approve = el('button', 'button button-primary', 'Aprovar frame');
  approve.type = 'submit';
  approve.name = 'decision';
  approve.value = 'aprovada';
  const reject = el('button', 'button button-danger', 'Rejeitar frame');
  reject.type = 'submit';
  reject.name = 'decision';
  reject.value = 'rejeitada';
  actions.append(approve, reject);
  body.append(reasonLabel, confirmation, actions);
  form.append(body);
  form.addEventListener('submit', (event) => submitImageReview(event, production, clip));
  return form;
}

function renderReviews() {
  const root = document.querySelector('#review-grid');
  root.replaceChildren();
  const reviews = [];
  state.dashboard.producoes
    .filter((production) => production.ativa)
    .forEach((production) => {
      production.clipes
        .filter((clip) => clip.aprovacao_necessaria
          && clip.imagem?.valido
          && !clip.video)
        .forEach((clip) => reviews.push({ production, clip }));
    });
  document.querySelector('#review-result-count').textContent =
    formatNumber(reviews.length) + ' frames disponíveis para revisão';
  if (!reviews.length) {
    root.append(emptyState('Nenhum frame ativo está disponível para decisão agora.'));
    return;
  }
  reviews.forEach(({ production, clip }) => root.append(reviewCard(production, clip)));
}

function characterCount(label, value, limit) {
  const length = String(value || '').length;
  const tone = length >= limit * .9 ? ' is-near-limit' : '';
  return el(
    'span',
    'character-count' + tone,
    label + ': ' + length + '/' + limit,
  );
}

function carouselCard(production, clip) {
  const content = clip.carrossel_conteudo || {};
  const generated = Boolean(clip.carrossel?.valido);
  const sourceValid = Boolean(clip.imagem?.valido);
  const form = el('form', 'carousel-card');
  form.append(mediaPreview(
    generated ? clip.carrossel : clip.imagem,
    'media-preview carousel-preview',
    generated ? 'card de ' + clip.id : 'imagem base de ' + clip.id,
  ));

  const heading = el('div', 'carousel-card-heading');
  const title = el('div');
  title.append(
    el('h3', '', clip.id),
    el('p', 'review-meta', humanize(clip.papel)),
  );
  heading.append(
    title,
    chip(generated ? 'Card gerado' : 'Pendente', generated ? 'success' : 'warning'),
  );

  const copy = el('div', 'carousel-copy');
  copy.append(
    el('strong', '', content.texto || 'Título não informado'),
    el('span', '', content.subtexto || 'Destaque não informado'),
  );
  if (content.cta) copy.append(el('span', 'carousel-cta', content.cta));

  const counts = el('div', 'character-counts');
  counts.append(
    characterCount('Título', content.texto, 52),
    characterCount('Destaque', content.subtexto, 28),
  );
  if (content.cta) counts.append(characterCount('CTA', content.cta, 54));

  const details = [];
  if (content.cta_destino) details.push('Destino: ' + content.cta_destino);
  if (content.cta_palavra) details.push('Palavra: ' + content.cta_palavra);
  details.push('Imagem ' + (clip.imagem?.sha256 || 'indisponível'));

  const confirmation = el('label', 'confirm-field');
  const checkbox = el('input');
  checkbox.type = 'checkbox';
  checkbox.name = 'confirm';
  checkbox.required = true;
  checkbox.disabled = !sourceValid;
  confirmation.append(
    checkbox,
    el('span', '', generated
      ? 'Confirmo a geração de uma nova versão local deste card.'
      : 'Confirmo este texto, este clipe e esta imagem base.'),
  );

  const button = el(
    'button',
    'button button-primary',
    generated ? 'Gerar novamente' : 'Gerar card local',
  );
  button.type = 'submit';
  button.disabled = !sourceValid;
  form.append(
    heading,
    copy,
    counts,
    el('p', 'carousel-details', details.join(' · ')),
    confirmation,
    button,
  );
  if (!sourceValid) {
    form.append(el('p', 'clip-error', 'Imagem base indisponível; registre-a antes de gerar.'));
  }
  form.addEventListener(
    'submit',
    (event) => submitCarousel(event, production, clip, generated),
  );
  return form;
}

function renderCarousels() {
  const root = document.querySelector('#carousel-list');
  root.replaceChildren();
  let total = 0;
  let generated = 0;
  state.dashboard.producoes
    .filter((production) => production.ativa)
    .forEach((production) => {
      const clips = production.clipes.filter((clip) => clip.carrossel_solicitado);
      if (!clips.length) return;
      total += clips.length;
      generated += clips.filter((clip) => clip.carrossel?.valido).length;
      const section = el('section', 'carousel-production');
      const heading = el('div', 'carousel-production-heading');
      heading.append(
        el('h2', '', production.id),
        el('span', 'production-meta', 'Revisão ' + production.revisao + ' · ' + clips.length + ' cards'),
      );
      const grid = el('div', 'carousel-grid');
      clips.forEach((clip) => grid.append(carouselCard(production, clip)));
      section.append(heading, grid);
      root.append(section);
    });
  document.querySelector('#carousel-result-count').textContent =
    formatNumber(total) + ' cards autorizados · ' + formatNumber(generated) + ' gerados';
  if (!total) {
    root.append(emptyState('Nenhum carrossel foi autorizado nas revisões ativas.'));
  }
}

function executionFor(production, clip) {
  return (state.executions.execucoes || []).find(
    (item) => item.producao_id === production.id
      && item.revisao === production.revisao
      && item.id_clipe === clip.id,
  );
}

function videoReadiness(production, clip) {
  const execution = executionFor(production, clip);
  if (clip.video?.valido) {
    return { key: 'completed', label: 'Vídeo concluído', tone: 'success', execution };
  }
  if (execution && ['queued', 'running'].includes(execution.status)) {
    return {
      key: 'running',
      label: humanize(execution.status),
      tone: 'info',
      detail: 'A tarefa está ativa. O painel atualiza automaticamente.',
      execution,
    };
  }
  if (execution?.status === 'succeeded') {
    return {
      key: 'running',
      label: 'Finalizando registro',
      tone: 'info',
      detail: execution.resultado || 'A saída foi concluída e será recarregada.',
      execution,
    };
  }
  if (clip.tentativa) {
    return {
      key: 'interrupted',
      label: 'Tentativa exige conferência',
      tone: 'error',
      detail: 'Não reenvie. Confira o Flow, execucao.json e gflow.log antes de decidir a retomada.',
      execution,
    };
  }
  if (clip.lock_ativo) {
    return {
      key: 'running',
      label: 'Clipe bloqueado por operação ativa',
      tone: 'info',
      detail: 'Aguarde a liberação do lock do clipe.',
      execution,
    };
  }
  if (!clip.imagem?.valido) {
    return { key: 'blocked', label: 'Imagem indisponível', tone: 'error', execution };
  }
  if (!clip.aprovacao_humana || !clip.aprovacao_vinculada) {
    return {
      key: 'blocked',
      label: 'Aprovação vinculada pendente',
      tone: 'warning',
      detail: 'Revise e aprove a imagem atual antes de liberar créditos.',
      execution,
    };
  }
  const executor = state.executions.executor || {};
  if (!executor.gflow_disponivel) {
    return {
      key: 'blocked',
      label: 'gflow.exe não encontrado',
      tone: 'error',
      detail: 'Execute o instalador ou corrija GFLOW_ROOT antes de gerar vídeo.',
      execution,
    };
  }
  if (!executor.projeto_configurado) {
    return {
      key: 'blocked',
      label: 'Projeto Flow não configurado',
      tone: 'error',
      detail: 'Defina GFLOW_PROJECT_ID antes de tentar gerar vídeo.',
      execution,
    };
  }
  return {
    key: 'ready',
    label: execution?.status === 'failed' ? 'Pronto para tentar novamente' : 'Pronto para liberar',
    tone: 'success',
    detail: execution?.erro || 'Todas as travas locais foram atendidas.',
    execution,
  };
}

function videoCard(production, clip) {
  const readiness = videoReadiness(production, clip);
  const form = el('form', 'video-card is-' + readiness.key);
  form.append(mediaPreview(
    clip.video?.valido ? clip.video : clip.imagem,
    'media-preview video-preview',
    clip.video?.valido ? 'vídeo de ' + clip.id : 'frame de ' + clip.id,
  ));
  const body = el('div', 'video-body');
  const heading = el('div', 'video-heading');
  const title = el('div');
  title.append(
    el('h2', '', clip.id),
    el('p', 'review-meta', production.id + ' · revisão ' + production.revisao),
  );
  heading.append(title, chip(readiness.label, readiness.tone));

  const facts = el('div', 'video-facts');
  facts.append(
    chip(clip.metodo_video || 'método não informado'),
    chip((clip.duracao_video_s || '—') + ' s'),
    chip(
      clip.aprovacao_vinculada ? 'Aprovação vinculada' : 'Sem vínculo técnico',
      clip.aprovacao_vinculada ? 'success' : 'warning',
    ),
    chip('Modelo ' + (state.executions.executor?.modelo || 'não informado')),
  );

  const detail = el(
    'div',
    'video-status-detail' + (readiness.key === 'interrupted' ? ' is-error' : ''),
    readiness.detail || 'Estado atualizado a partir dos arquivos locais.',
  );
  body.append(heading, facts, detail);

  if (readiness.execution) {
    const execution = readiness.execution;
    body.append(el(
      'p',
      'review-meta',
      'Solicitada em ' + formatDate(execution.solicitada_em)
        + (execution.concluida_em ? ' · concluída em ' + formatDate(execution.concluida_em) : ''),
    ));
  }

  if (readiness.key === 'ready') {
    const phrase = el('label', 'credit-confirmation');
    const phraseInput = el('input');
    phraseInput.type = 'text';
    phraseInput.name = 'credit_confirmation';
    phraseInput.placeholder = 'GERAR VIDEO';
    phraseInput.autocomplete = 'off';
    phraseInput.spellcheck = false;
    phraseInput.required = true;
    phrase.append(
      el('span', '', 'Para autorizar possível consumo, digite GERAR VIDEO'),
      phraseInput,
    );
    const confirmation = el('label', 'confirm-field');
    const checkbox = el('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'confirm';
    checkbox.required = true;
    confirmation.append(
      checkbox,
      el('span', '', 'Confirmo este clipe, este frame e o possível consumo de créditos.'),
    );
    const button = el('button', 'button button-danger', 'Gerar vídeo no Flow');
    button.type = 'submit';
    body.append(phrase, confirmation, button);
    form.addEventListener(
      'submit',
      (event) => submitVideo(event, production, clip),
    );
  }
  form.append(body);
  return form;
}

function renderVideos() {
  const root = document.querySelector('#video-list');
  const summary = document.querySelector('#executor-summary');
  root.replaceChildren();
  summary.replaceChildren();
  const executor = state.executions.executor || {};
  summary.append(
    chip('Modelo ' + (executor.modelo || 'não informado'), 'info'),
    chip('Timeout ' + formatNumber(executor.timeout_segundos) + ' s'),
    chip(executor.gflow_disponivel ? 'gflow disponível' : 'gflow ausente', executor.gflow_disponivel ? 'success' : 'error'),
    chip(executor.projeto_configurado ? 'Projeto configurado' : 'Projeto ausente', executor.projeto_configurado ? 'success' : 'error'),
    chip('Máximo: 1 execução paga', 'warning'),
  );
  const items = [];
  state.dashboard.producoes
    .filter((production) => production.ativa)
    .forEach((production) => production.clipes
      .filter((clip) => clip.gera_video)
      .forEach((clip) => items.push({ production, clip })));
  let ready = 0;
  let active = 0;
  let completed = 0;
  items.forEach(({ production, clip }) => {
    const status = videoReadiness(production, clip).key;
    if (status === 'ready') ready += 1;
    if (status === 'running') active += 1;
    if (status === 'completed') completed += 1;
    root.append(videoCard(production, clip));
  });
  document.querySelector('#video-result-count').textContent =
    formatNumber(items.length) + ' vídeos planejados · '
    + formatNumber(ready) + ' prontos · '
    + formatNumber(active) + ' em andamento · '
    + formatNumber(completed) + ' concluídos';
  if (!items.length) root.append(emptyState('Nenhum vídeo foi solicitado nas revisões ativas.'));
}

function deliveryMedia(item) {
  const media = {
    url: item.url,
    valido: item.disponivel,
    extensao: String(item.entrega || '').match(/\.[^.]+$/)?.[0],
  };
  return mediaPreview(media, 'delivery-media', `entrega ${item.sequencia || 'sem número'}`);
}

function renderDeliveries() {
  const root = document.querySelector('#delivery-grid');
  root.replaceChildren();
  if (!state.deliveries.length) {
    root.append(emptyState('Nenhuma entrega indexada.'));
    return;
  }
  [...state.deliveries].sort((a, b) => Number(b.sequencia || 0) - Number(a.sequencia || 0)).forEach((item) => {
    const card = el('article', 'delivery');
    const body = el('div', 'delivery-body');
    body.append(
      chip(humanize(item.tipo), item.disponivel ? 'success' : 'error'),
      el('h3', '', `Entrega ${item.sequencia || '—'}`),
      el('p', '', item.entrega || 'Caminho não informado'),
    );
    card.append(deliveryMedia(item), body);
    root.append(card);
  });
}

function renderOverviewMessage() {
  const actions = state.dashboard.proximas_acoes;
  const review = actions.revisar_e_aprovar_imagem || 0;
  const image = actions.gerar_imagem || 0;
  const parts = [];
  if (review) parts.push(`${formatNumber(review)} clipes aguardam revisão humana`);
  if (image) parts.push(`${formatNumber(image)} precisa de imagem`);
  document.querySelector('#overview-message').textContent = parts.length
    ? `${parts.join(' e ')}. Nenhuma ação é executada automaticamente.`
    : 'Não há ação humana pendente no recorte atual.';
  document.querySelector('#updated-at').textContent = `Atualizado em ${formatDate(state.dashboard.gerado_em)}`;
}

function setFeedback(selector, kind, message) {
  const feedback = document.querySelector(selector);
  feedback.setAttribute('tabindex', '-1');
  feedback.className = `operation-feedback ${kind ? `is-${kind}` : ''}`.trim();
  feedback.textContent = message;
  if (message) feedback.focus({ preventScroll: true });
}

function setOperationFeedback(kind, message) {
  setFeedback('#operation-feedback', kind, message);
}

function setReviewFeedback(kind, message) {
  setFeedback('#review-feedback', kind, message);
}

function setCarouselFeedback(kind, message) {
  setFeedback('#carousel-feedback', kind, message);
}

function setVideoFeedback(kind, message) {
  setFeedback('#video-feedback', kind, message);
}

function fillSelect(select, placeholder, items) {
  const previous = select.value;
  select.replaceChildren(new Option(placeholder, ''));
  items.forEach((item) => select.append(new Option(item.label, item.value)));
  if ([...select.options].some((option) => option.value === previous)) {
    select.value = previous;
  }
}

function populateResponseOptions() {
  const packageId = document.querySelector('#import-package').value;
  const selected = state.operations.pacotes.find((item) => item.id === packageId);
  const responses = state.operations.respostas
    .filter((item) => !selected || item.pacote_sha256 === selected.pacote_sha256)
    .map((item) => ({
      value: item.id,
      label: `${item.producao_id || 'Produção não informada'} · ${item.id}`,
    }));
  fillSelect(document.querySelector('#import-response'), 'Selecionar resposta', responses);
}

function populateClipOptions() {
  const value = document.querySelector('#image-production').value;
  const production = state.dashboard.producoes
    .find((item) => `${item.id}/${item.revisao}` === value);
  const clips = (production?.clipes || []).map((clip) => ({
    value: clip.id,
    label: `${clip.id} · ${humanize(clip.proxima_acao)}`,
  }));
  fillSelect(document.querySelector('#image-clip'), 'Selecionar clipe', clips);
}

function populateOperations() {
  const packages = state.operations.pacotes.map((item) => ({
    value: item.id,
    label: `${item.producao_id} · revisão ${item.revisao} · ${item.clipes} clipes`,
  }));
  fillSelect(document.querySelector('#import-package'), 'Selecionar pacote', packages);
  populateResponseOptions();
  const productions = state.dashboard.producoes
    .filter((item) => item.ativa)
    .map((item) => ({
      value: `${item.id}/${item.revisao}`,
      label: `${item.id} · revisão ${item.revisao}`,
    }));
  fillSelect(document.querySelector('#image-production'), 'Selecionar produção', productions);
  populateClipOptions();
  const latest = document.querySelector('#latest-package-link');
  latest.hidden = !state.operations.pacote_ia?.disponivel;
  if (state.operations.pacote_ia?.url) latest.href = state.operations.pacote_ia.url;
}

const assistantSingleClipActivities = new Set([
  'image-register',
  'approve',
  'video',
]);

function powershellQuote(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

function assistantProduction() {
  const value = document.querySelector('#assistant-production').value;
  return (state.dashboard?.producoes || [])
    .find((item) => `${item.id}/${item.revisao}` === value);
}

function populateAssistantClips() {
  const activity = document.querySelector('#assistant-activity').value;
  const production = assistantProduction();
  const clips = (production?.clipes || [])
    .filter((clip) => clip.plano_status !== 'pendente')
    .map((clip) => ({
      value: clip.id,
      label: `${clip.id} · ${humanize(clip.proxima_acao)}`,
    }));
  const placeholder = assistantSingleClipActivities.has(activity)
    ? 'Selecionar clipe'
    : 'Todos os clipes';
  fillSelect(document.querySelector('#assistant-clip'), placeholder, clips);
}

function assistantContext() {
  const activity = document.querySelector('#assistant-activity').value;
  const production = assistantProduction();
  const clipId = document.querySelector('#assistant-clip').value;
  const instruction = document.querySelector('#assistant-instruction').value.trim();
  const rawImage = document.querySelector('#assistant-image').value.trim();
  const requiresProduction = activity !== 'pipeline';
  const requiresClip = assistantSingleClipActivities.has(activity);

  if (requiresProduction && !production) {
    return { error: 'Selecione uma produção ativa para montar este comando.' };
  }
  if (requiresClip && !clipId) {
    return { error: 'Selecione um clipe específico para esta atividade.' };
  }
  if (activity === 'image-register' && !rawImage) {
    return { error: 'Informe o nome ou caminho da imagem que será registrada.' };
  }

  let productionSetup = '';
  let clipSetup = '';
  let productionArg = '';
  let clipArg = '';
  if (production) {
    const path = production.pasta.replaceAll('/', '\\');
    const localPath = /^[A-Za-z]:\\/.test(path) ? path : `.\\${path}`;
    productionSetup = `$Producao = (Resolve-Path ${powershellQuote(localPath)}).Path`;
    productionArg = ' --producao $Producao';
  }
  if (clipId) {
    clipSetup = `$Clipe = ${powershellQuote(clipId)}`;
    clipArg = ' --clipe $Clipe';
  }
  const prefix = [productionSetup, clipSetup].filter(Boolean);
  const note = instruction ? `Considere sua observação antes de executar: “${instruction}”` : null;
  const result = {
    command: '',
    cost: 'Sem chamada paga',
    costTone: 'local',
    steps: [],
    summary: '',
    title: '',
  };

  if (activity === 'pipeline') {
    Object.assign(result, {
      title: 'Continuar todo o pipeline',
      cost: 'Pode consumir créditos',
      costTone: 'credit',
      summary: 'Retoma todas as produções ativas e para quando houver uma decisão humana pendente.',
      steps: [
        'Salve e feche a planilha antes de começar.',
        note,
        'Execute o comando e leia o resumo final. Imagens e vídeos liberados podem ser enviados ao Flow.',
        'Se o resumo pedir revisão, abra a imagem no painel, aprove ou rejeite e rode o mesmo comando novamente.',
      ],
      command: 'python scripts\\rodar_pipeline.py --modelo-video omni-flash',
    });
  } else if (activity === 'status') {
    Object.assign(result, {
      title: 'Consultar o estado atual',
      summary: 'Lista planos e estados sem gerar mídia nem alterar aprovações.',
      steps: [
        note,
        clipId ? 'Confira o estado do clipe selecionado.' : 'Confira o estado de todos os clipes desta produção.',
        'Use a próxima ação indicada no resultado para decidir o passo seguinte.',
      ],
      command: [...prefix, `python scripts\\executar_flow.py listar${productionArg}${clipArg}`].join('\n'),
    });
  } else if (activity === 'image-preview' || activity === 'image-generate') {
    const execute = activity === 'image-generate';
    Object.assign(result, {
      title: execute ? 'Gerar imagem no Flow' : 'Simular geração de imagem',
      cost: execute ? 'Pode consumir créditos' : 'Sem chamada paga',
      costTone: execute ? 'credit' : 'local',
      summary: execute
        ? 'Envia ao Flow apenas as imagens pendentes da seleção.'
        : 'Mostra o que seria gerado, mas não envia nada ao Flow.',
      steps: [
        note,
        execute
          ? 'Revise antes o prompt e as referências do clipe.'
          : 'Leia a simulação e confirme se produção, clipe, prompt e referências estão corretos.',
        execute
          ? 'Execute uma única vez e aguarde o relatório final antes de tentar novamente.'
          : 'Quando estiver tudo correto, escolha “Gerar imagem no Flow” nesta mesma tela.',
      ],
      command: [
        ...prefix,
        `python scripts\\gerar_imagens.py${productionArg}${clipArg}${execute ? ' --executar' : ''}`,
      ].join('\n'),
    });
  } else if (activity === 'image-register') {
    let imagePath = rawImage.replaceAll('/', '\\');
    if (!imagePath.includes('\\')) imagePath = `entradas\\${imagePath}`;
    if (!/^(?:[A-Za-z]:\\|\.\\)/.test(imagePath)) imagePath = `.\\${imagePath}`;
    Object.assign(result, {
      title: 'Usar uma imagem pronta',
      summary: 'Copia a imagem para a revisão ativa e revoga qualquer aprovação técnica anterior.',
      steps: [
        'Confirme que a imagem informada existe e pertence ao clipe selecionado.',
        note,
        'Execute o comando. A imagem original não será movida nem alterada.',
        'Depois abra o novo frame, revise-o e registre uma nova aprovação.',
      ],
      command: [
        ...prefix,
        `$Imagem = (Resolve-Path ${powershellQuote(imagePath)}).Path`,
        `python scripts\\executar_flow.py registrar-imagem${productionArg}${clipArg} --arquivo $Imagem`,
      ].join('\n'),
    });
  } else if (activity === 'approve') {
    Object.assign(result, {
      title: 'Vincular imagem aprovada',
      summary: 'Registra tecnicamente a sua decisão humana para o frame atual.',
      steps: [
        'Abra o frame e confira produto, anatomia, identidade, cenário e enquadramento.',
        'Na planilha, escreva “aprovada” na coluna aprovacao, salve e feche o Excel.',
        note,
        'Execute o comando. Ele não gera mídia.',
      ],
      command: [...prefix, `python scripts\\executar_flow.py aprovar${productionArg}${clipArg}`].join('\n'),
    });
  } else if (activity === 'carousel') {
    Object.assign(result, {
      title: 'Gerar carrossel',
      summary: 'Renderiza localmente os cards autorizados pelo plano e preserva versões anteriores.',
      steps: [
        note,
        clipId ? 'Será processado somente o clipe selecionado.' : 'Serão processados os carrosséis ativos da produção.',
        'Execute o comando e procure o resultado em entregas_flow\\carrossel.',
      ],
      command: [...prefix, `python scripts\\gerar_carrossel.py${productionArg}${clipArg}`].join('\n'),
    });
  } else if (activity === 'video') {
    Object.assign(result, {
      title: 'Gerar vídeo aprovado',
      cost: 'Pode consumir créditos',
      costTone: 'credit',
      summary: 'Gera um vídeo de oito segundos com omni-flash a partir do frame aprovado e vinculado.',
      steps: [
        'Confirme que o frame atual está aprovado e que o comando de aprovação já foi concluído.',
        note,
        'Execute uma única vez e aguarde a conclusão. Não repita enquanto houver tentativa em andamento.',
        'Revise o MP4 entregue antes de considerar o clipe concluído.',
      ],
      command: [
        ...prefix,
        `python scripts\\executar_flow.py video${productionArg}${clipArg} --modelo-video omni-flash`,
      ].join('\n'),
    });
  }
  result.steps = result.steps.filter(Boolean);
  return result;
}

function renderAssistant() {
  const activity = document.querySelector('#assistant-activity').value;
  const usesSelection = activity !== 'pipeline';
  const requiresClip = assistantSingleClipActivities.has(activity);
  document.querySelector('#assistant-production-field').hidden = !usesSelection;
  document.querySelector('#assistant-clip-field').hidden = !usesSelection;
  document.querySelector('#assistant-image-field').hidden = activity !== 'image-register';
  document.querySelector('#assistant-production').required = usesSelection;
  document.querySelector('#assistant-clip').required = requiresClip;

  const context = assistantContext();
  const title = document.querySelector('#assistant-result-title');
  const summary = document.querySelector('#assistant-summary');
  const cost = document.querySelector('#assistant-cost');
  const steps = document.querySelector('#assistant-steps');
  const code = document.querySelector('#assistant-command code');
  const copy = document.querySelector('#copy-command');
  document.querySelector('#copy-status').textContent = '';
  steps.replaceChildren();

  if (context.error) {
    title.textContent = 'Complete os campos';
    summary.textContent = context.error;
    cost.textContent = 'Aguardando dados';
    cost.className = 'assistant-cost';
    code.textContent = '';
    copy.disabled = true;
    return;
  }
  title.textContent = context.title;
  summary.textContent = context.summary;
  cost.textContent = context.cost;
  cost.className = `assistant-cost is-${context.costTone}`;
  context.steps.forEach((item) => steps.append(el('li', '', item)));
  code.textContent = context.command;
  copy.disabled = false;
}

function populateAssistant() {
  const productions = (state.dashboard?.producoes || [])
    .filter((item) => item.ativa)
    .map((item) => ({
      value: `${item.id}/${item.revisao}`,
      label: `${item.id} · revisão ${item.revisao}`,
    }));
  fillSelect(
    document.querySelector('#assistant-production'),
    'Selecionar produção',
    productions,
  );
  populateAssistantClips();
  renderAssistant();
}

async function copyAssistantCommand() {
  const command = document.querySelector('#assistant-command code').textContent;
  if (!command) return;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(command);
    } else {
      const fallback = el('textarea');
      fallback.value = command;
      fallback.setAttribute('readonly', '');
      fallback.className = 'sr-only';
      document.body.append(fallback);
      fallback.select();
      document.execCommand('copy');
      fallback.remove();
    }
    document.querySelector('#copy-status').textContent = 'Comando copiado.';
    announce('Comando copiado para a área de transferência.');
  } catch (_error) {
    document.querySelector('#copy-status').textContent = 'Não foi possível copiar. Selecione o comando acima manualmente.';
  }
}

async function postOperation(url, content, contentType = 'application/octet-stream') {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'X-Pipeline-Confirmation': 'confirmar',
      ...(content ? { 'Content-Type': contentType } : {}),
    },
    body: content || null,
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || `Falha ${response.status}`);
  return result;
}

async function runOperation(form, description, callback) {
  if (!form.reportValidity()) return;
  if (!window.confirm(`${description}\n\nDeseja continuar?`)) return;
  const button = form.querySelector('button[type=submit]');
  button.disabled = true;
  setOperationFeedback('', `${description} em andamento…`);
  try {
    const result = await callback();
    setOperationFeedback(
      result.aviso ? 'warning' : 'success',
      result.resultado || 'Operação concluída com sucesso.',
    );
    form.reset();
    await loadData();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setOperationFeedback('error', message);
    announce(`Falha na operação: ${message}`);
  } finally {
    button.disabled = false;
  }
}

async function submitImageReview(event, production, clip) {
  event.preventDefault();
  const form = event.currentTarget;
  const decision = event.submitter?.value;
  const reason = form.elements.reason;
  const rejectWithoutReason = decision === 'rejeitada' && !reason.value.trim();
  reason.setCustomValidity(
    rejectWithoutReason ? 'Informe por que o frame foi rejeitado.' : '',
  );
  if (!form.reportValidity() || !decision) return;

  const verb = decision === 'aprovada' ? 'Aprovar' : 'Rejeitar';
  const description = verb + ' o frame ' + clip.id
    + ' da revisão ' + production.revisao
    + ' (SHA-256 ' + clip.imagem.sha256.slice(0, 12) + '…)';
  if (!window.confirm(description + '\n\nEsta ação não gera vídeo. Deseja continuar?')) return;

  const buttons = [...form.querySelectorAll('button[type=submit]')];
  buttons.forEach((button) => { button.disabled = true; });
  setReviewFeedback('', description + '…');
  try {
    const result = await postOperation(
      '/api/operations/review-image',
      JSON.stringify({
        production_id: production.id,
        revision: production.revisao,
        clip_id: clip.id,
        decision,
        image_sha256: clip.imagem.sha256,
        reason: decision === 'rejeitada' ? reason.value.trim() : '',
      }),
      'application/json',
    );
    setReviewFeedback('success', result.resultado);
    form.reset();
    await loadData();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setReviewFeedback('error', message);
    announce('Falha ao registrar a revisão: ' + message);
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
}

async function submitCarousel(event, production, clip, regenerate) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const action = regenerate ? 'Gerar nova versão' : 'Gerar card';
  const description = action + ' para ' + clip.id
    + ' da revisão ' + production.revisao
    + ' (imagem ' + clip.imagem.sha256.slice(0, 12) + '…)';
  if (!window.confirm(description + '\n\nA operação é local e não gera vídeo. Deseja continuar?')) return;
  const button = form.querySelector('button[type=submit]');
  button.disabled = true;
  setCarouselFeedback('', description + '…');
  try {
    const result = await postOperation(
      '/api/operations/generate-carousel',
      JSON.stringify({
        production_id: production.id,
        revision: production.revisao,
        clip_id: clip.id,
        image_sha256: clip.imagem.sha256,
        regenerate,
      }),
      'application/json',
    );
    setCarouselFeedback('success', result.resultado);
    form.reset();
    await loadData();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setCarouselFeedback('error', message);
    announce('Falha ao gerar o carrossel: ' + message);
  } finally {
    button.disabled = false;
  }
}

async function submitVideo(event, production, clip) {
  event.preventDefault();
  const form = event.currentTarget;
  const phrase = form.elements.credit_confirmation;
  const confirmedPhrase = phrase.value.trim().toUpperCase();
  phrase.setCustomValidity(
    confirmedPhrase === 'GERAR VIDEO'
      ? ''
      : 'Digite exatamente GERAR VIDEO.',
  );
  if (!form.reportValidity()) return;
  const model = state.executions.executor?.modelo || 'modelo configurado';
  const description = 'Gerar vídeo para ' + clip.id
    + ' da revisão ' + production.revisao
    + ' usando ' + model
    + ' (frame ' + clip.imagem.sha256.slice(0, 12) + '…)';
  if (!window.confirm(
    description
      + '\n\nEsta ação pode consumir créditos reais. Somente uma execução será iniciada. Deseja continuar?',
  )) return;
  const button = form.querySelector('button[type=submit]');
  button.disabled = true;
  setVideoFeedback('', description + '…');
  try {
    const result = await postOperation(
      '/api/operations/generate-video',
      JSON.stringify({
        production_id: production.id,
        revision: production.revisao,
        clip_id: clip.id,
        image_sha256: clip.imagem.sha256,
        credit_confirmation: confirmedPhrase,
      }),
      'application/json',
    );
    setVideoFeedback(
      'success',
      'Execução ' + result.id.slice(0, 8) + ' iniciada. Acompanhe o estado abaixo.',
    );
    form.reset();
    await loadData();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setVideoFeedback('error', message);
    announce('Falha ao liberar o vídeo: ' + message);
  } finally {
    button.disabled = false;
  }
}

function renderAll() {
  renderOverviewMessage();
  renderKpis();
  renderActions();
  renderDiagnostics();
  renderEvents('#recent-events', state.dashboard.ultimos_eventos || [], 5);
  populateFilters();
  renderProductions();
  renderReviews();
  renderCarousels();
  renderVideos();
  renderDeliveries();
  renderEvents('#event-list', state.events, 100);
  populateOperations();
  populateAssistant();
}

async function getJson(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Falha ${response.status} ao consultar ${url}`);
  return response.json();
}

async function loadData() {
  const button = document.querySelector('#refresh-button');
  const main = document.querySelector('#conteudo');
  const buttonLabel = button.textContent;
  button.disabled = true;
  button.textContent = 'Atualizando…';
  main.setAttribute('aria-busy', 'true');
  setConnection('', 'Atualizando…');
  try {
    const [dashboard, deliveries, logs, operations, executions] = await Promise.all([
      getJson('/api/dashboard'),
      getJson('/api/deliveries'),
      getJson('/api/logs?limit=100'),
      getJson('/api/operations'),
      getJson('/api/operations/executions'),
    ]);
    state.dashboard = dashboard;
    state.deliveries = deliveries.entregas || [];
    state.events = logs.eventos || [];
    state.operations = operations;
    state.executions = executions;
    renderAll();
    setConnection('online', 'Dados locais atualizados');
    announce('Painel atualizado com sucesso.');
  } catch (error) {
    setConnection('error', 'Falha na leitura local');
    const message = error instanceof Error ? error.message : String(error);
    document.querySelector('#overview-message').textContent = message;
    const loadFailure = 'Não foi possível carregar estes dados. Verifique se o servidor local está ativo e tente atualizar.';
    [
      '#kpi-grid',
      '#action-bars',
      '#diagnostics-list',
      '#recent-events',
      '#production-list',
      '#review-grid',
      '#carousel-list',
      '#video-list',
      '#delivery-grid',
      '#event-list',
    ].forEach((selector) => {
      document.querySelector(selector).replaceChildren(emptyState(loadFailure));
    });
    announce('Falha ao atualizar o painel.');
  } finally {
    button.disabled = false;
    button.textContent = buttonLabel;
    main.setAttribute('aria-busy', 'false');
  }
}

const navigationTabs = [...document.querySelectorAll('.nav-tab')];

navigationTabs.forEach((button) => {
  button.addEventListener('click', () => setView(button.dataset.view));
  button.addEventListener('keydown', (event) => {
    const supportedKeys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
    if (!supportedKeys.includes(event.key)) return;
    event.preventDefault();
    const current = navigationTabs.indexOf(button);
    let next = current;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = navigationTabs.length - 1;
    if (event.key === 'ArrowLeft') {
      next = (current - 1 + navigationTabs.length) % navigationTabs.length;
    }
    if (event.key === 'ArrowRight') next = (current + 1) % navigationTabs.length;
    const nextTab = navigationTabs[next];
    setView(nextTab.dataset.view);
    nextTab.focus({ preventScroll: true });
    nextTab.scrollIntoView({ behavior: 'auto', block: 'nearest', inline: 'nearest' });
  });
});
document.querySelectorAll('[data-go]').forEach((button) => {
  button.addEventListener('click', () => setView(button.dataset.go, true, true));
});
document.querySelector('#refresh-button').addEventListener('click', loadData);
document.querySelector('#production-filters').addEventListener('input', renderProductions);
document.querySelector('#production-filters').addEventListener('change', renderProductions);
document.querySelector('#clear-filters').addEventListener('click', () => {
  document.querySelector('#production-filters').reset();
  renderProductions();
  document.querySelector('#search-input').focus();
});
document.querySelector('#import-package').addEventListener('change', populateResponseOptions);
document.querySelector('#image-production').addEventListener('change', populateClipOptions);
document.querySelector('#assistant-activity').addEventListener('change', () => {
  populateAssistantClips();
  renderAssistant();
});
document.querySelector('#assistant-production').addEventListener('change', () => {
  populateAssistantClips();
  renderAssistant();
});
document.querySelector('#assistant-clip').addEventListener('change', renderAssistant);
document.querySelector('#assistant-image').addEventListener('input', renderAssistant);
document.querySelector('#assistant-instruction').addEventListener('input', renderAssistant);
document.querySelector('#copy-command').addEventListener('click', copyAssistantCommand);

document.querySelector('#prepare-form').addEventListener('submit', (event) => {
  event.preventDefault();
  runOperation(
    event.currentTarget,
    'Preparar pacotes e atualizar o ZIP consolidado',
    async () => {
      const result = await postOperation('/api/operations/prepare');
      const count = result.preparacao?.pacotes?.length || 0;
      const pending = result.preparacao?.pendencias?.length || 0;
      return {
        ...result,
        resultado: `${formatNumber(count)} pacotes preparados · ${formatNumber(pending)} pendências`,
      };
    },
  );
});

document.querySelector('#import-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const packageId = document.querySelector('#import-package').value;
  const responseId = document.querySelector('#import-response').value;
  const file = document.querySelector('#import-file').files[0];
  const responseSelect = document.querySelector('#import-response');
  responseSelect.setCustomValidity(file || responseId ? '' : 'Selecione ou envie uma resposta JSON.');
  runOperation(form, `Importar resposta no pacote ${packageId}`, async () => {
    const params = new URLSearchParams({ package_id: packageId });
    let result;
    if (file) {
      params.set('filename', file.name);
      result = await postOperation(
        `/api/operations/import-upload?${params}`,
        await file.arrayBuffer(),
      );
    } else {
      params.set('response_id', responseId);
      result = await postOperation(`/api/operations/import?${params}`);
    }
    return {
      ...result,
      aviso: Boolean(result.erro_excel),
      resultado: result.erro_excel
        ? `Revisão criada, mas a planilha não foi atualizada: ${result.erro_excel}`
        : `${formatNumber(result.clipes)} clipes importados e validados`,
    };
  });
});

document.querySelector('#register-image-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const productionValue = document.querySelector('#image-production').value;
  const [productionId, revision] = productionValue.split('/');
  const clipId = document.querySelector('#image-clip').value;
  const file = document.querySelector('#image-file').files[0];
  runOperation(
    event.currentTarget,
    `Registrar ${file?.name || 'imagem'} no clipe ${clipId}`,
    async () => {
      const params = new URLSearchParams({
        production_id: productionId,
        revision,
        clip_id: clipId,
        filename: file.name,
      });
      return postOperation(
        `/api/operations/register-image?${params}`,
        await file.arrayBuffer(),
      );
    },
  );
});

function executionNeedsRefresh() {
  const dashboardTime = Date.parse(state.dashboard?.gerado_em || '') || 0;
  return (state.executions.execucoes || []).some((execution) => {
    if (['queued', 'running'].includes(execution.status)) return true;
    const finishedTime = Date.parse(execution.concluida_em || '') || 0;
    return finishedTime > dashboardTime;
  });
}

setInterval(() => {
  const refresh = document.querySelector('#refresh-button');
  if (
    document.visibilityState === 'visible'
    && executionNeedsRefresh()
    && !refresh.disabled
  ) {
    loadData();
  }
}, 3000);

const requestedView = window.location.hash.slice(1);
if (document.getElementById(requestedView)?.dataset.section) {
  setView(requestedView, false);
}
loadData().finally(() => window.scrollTo({ top: 0, behavior: 'auto' }));
