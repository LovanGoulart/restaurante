(() => {
  "use strict";
  const root = document.querySelector("#sales-report-page");
  if (!root) return;
  const data = JSON.parse(document.querySelector("#sales-chart-data").textContent);
  const money = value => (value / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const axisMoney = value => value >= 100000
    ? `R$ ${(value / 100).toLocaleString("pt-BR", { notation: "compact", maximumFractionDigits: 1 })}`
    : money(value);
  const tabs = [...root.querySelectorAll("[data-sales-tab]")];
  const ns = "http://www.w3.org/2000/svg";
  function node(tag, attrs = {}, text) {
    const element = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function trend(container) {
    const values = data.evolucao;
    if (!values.length) return;
    const width = Math.max(280, container.clientWidth), height = container.clientHeight || 255;
    const left = width < 500 ? 65 : 85, right = 20, top = 18, bottom = 35;
    const maximum = Math.max(100, ...values.map(item => item.value));
    const x = index => left + index * (width - left - right) / Math.max(1, values.length - 1);
    const y = value => top + (height - top - bottom) * (1 - value / maximum);
    const svg = node("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": `Vendas em ${values.length} intervalos; total ${money(values.reduce((sum, item) => sum + item.value, 0))}` });
    for (let i = 0; i <= 4; i++) {
      const value = maximum * i / 4;
      svg.append(node("line", { x1: left, x2: width - right, y1: y(value), y2: y(value), stroke: "#e8eef4" }));
      svg.append(node("text", { x: left - 10, y: y(value) + 4, "text-anchor": "end" }, axisMoney(value)));
    }
    const points = values.map((item, index) => `${x(index)},${y(item.value)}`).join(" ");
    svg.append(node("polygon", { points: `${left},${y(0)} ${points} ${x(values.length - 1)},${y(0)}`, fill: "#eaf2fb" }));
    svg.append(node("polyline", { points, fill: "none", stroke: "#4e86c4", "stroke-width": 2.5, "stroke-linejoin": "round" }));
    const step = Math.max(1, Math.ceil(values.length / (width < 500 ? 4 : 10)));
    values.forEach((item, index) => {
      const description = `${item.label}: ${money(item.value)}, ${item.orders} pedidos`;
      const point = node("circle", { cx: x(index), cy: y(item.value), r: 4, fill: "#4e86c4", stroke: "#fff", "stroke-width": 1.5, tabindex: "0", "aria-label": description });
      point.append(node("title", {}, description));
      svg.append(point);
      if (index % step === 0 || index === values.length - 1) {
        svg.append(node("text", { x: x(index), y: height - 10, "text-anchor": index === values.length - 1 ? "end" : index === 0 ? "start" : "middle" }, item.label.length === 10 ? item.label.slice(0, 5) : item.label));
      }
    });
    container.replaceChildren(svg);
  }
  function ranking(container, key) {
    const values = data[key];
    if (!values.length) {
      const empty = document.createElement("div");
      empty.className = "sales-empty";
      empty.textContent = "Sem dados para este período.";
      container.replaceChildren(empty);
      return;
    }
    const maximum = Math.max(1, ...values.map(item => item.value));
    const fragment = document.createDocumentFragment();
    values.forEach(item => {
      const row = document.createElement("div"); row.className = "sales-bar-row";
      const info = document.createElement("div"); info.className = "sales-bar-info";
      const name = document.createElement("span"); name.textContent = item.label;
      const value = document.createElement("strong");
      value.textContent = key === "produtos" ? `${item.value.toLocaleString("pt-BR")} un.` : money(item.value);
      info.append(name, value);
      const track = document.createElement("div"); track.className = "sales-bar-track"; track.setAttribute("aria-hidden", "true");
      const fill = document.createElement("div"); fill.className = "sales-bar-fill";
      fill.style.width = `${100 * Math.max(0, item.value) / maximum}%`;
      track.append(fill); row.append(info, track); fragment.append(row);
    });
    container.replaceChildren(fragment);
  }
  function charts() {
    root.querySelectorAll("[data-chart]").forEach(container => {
      if (container.closest("[role=tabpanel]").hidden) return;
      if (container.dataset.chart === "evolucao") trend(container);
      else ranking(container, container.dataset.chart);
    });
  }
  function activate(tab, focus = false) {
    const key = tab.dataset.salesTab;
    tabs.forEach(button => {
      const selected = button === tab;
      button.setAttribute("aria-selected", String(selected)); button.tabIndex = selected ? 0 : -1;
      document.getElementById(button.getAttribute("aria-controls")).hidden = !selected;
    });
    document.querySelector("#sales-tab-value").value = key;
    root.querySelectorAll("[data-period-link]").forEach(link => {
      const url = new URL(link.href); url.searchParams.set("aba", key); link.href = url;
    });
    const url = new URL(location.href); url.searchParams.set("aba", key); history.replaceState(null, "", url);
    if (focus) tab.focus({ preventScroll: true });
    charts();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab));
    tab.addEventListener("keydown", event => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); activate(tabs[next], true); }
    });
  });
  root.querySelectorAll("[data-paged-table]").forEach(table => {
    const rows = [...table.querySelectorAll("[data-sales-row]")], size = Number(table.dataset.pageSize);
    const controls = root.querySelector(`[data-pagination="${table.dataset.pagedTable}"]`);
    const previous = controls.querySelector("[data-page-prev]"), next = controls.querySelector("[data-page-next]");
    let page = 0;
    function update() {
      rows.forEach((row, index) => { row.hidden = index < page * size || index >= (page + 1) * size; });
      previous.disabled = page === 0; next.disabled = (page + 1) * size >= rows.length;
      controls.querySelector("[data-page-summary]").textContent = rows.length ? `${page * size + 1}–${Math.min((page + 1) * size, rows.length)} de ${rows.length}` : "Nenhum registro";
    }
    previous.addEventListener("click", () => { if (page > 0) { page--; update(); } });
    next.addEventListener("click", () => { if ((page + 1) * size < rows.length) { page++; update(); } });
    update();
  });
  charts();
  if ("ResizeObserver" in window) new ResizeObserver(charts).observe(root);
  else window.addEventListener("resize", charts);
})();
