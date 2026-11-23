"use strict";
(() => {
  const balanceNode = document.querySelector("#loyalty-balance");
  let busy = false;
  async function refresh() {
    if (!balanceNode || busy || document.hidden) return;
    busy = true;
    try {
      const data = await api("/api/fidelidade");
      balanceNode.textContent = data.saldo;
      document.querySelectorAll("[data-cost]").forEach(card => {
        const missing = Math.max(0, Number(card.dataset.cost) - data.saldo);
        card.querySelector("[data-availability]").textContent = missing ? "Faltam " + missing + " pontos" : "Você já pode resgatar!";
        card.querySelector("[data-redeem]").hidden = missing > 0;
      });
      const body = document.querySelector("#loyalty-history");
      body.replaceChildren();
      for (const m of data.historico) {
        const tr = document.createElement("tr");
        for (const value of [new Date(m.criado).toLocaleString(document.documentElement.lang), m.descricao, "#" + m.pedido, (m.pontos > 0 ? "+" : "") + m.pontos]) {
          const td = document.createElement("td");
          td.textContent = value;
          tr.append(td);
        }
        body.append(tr);
      }
      if (!data.historico.length) {
        const row = document.createElement("tr"), cell = document.createElement("td");
        cell.colSpan = 4; cell.textContent = "Nenhuma movimentação de pontos."; row.append(cell); body.append(row);
      }
      document.querySelector("#loyalty-update-status").textContent = "";
    } catch (e) {
      document.querySelector("#loyalty-update-status").textContent = e.message;
      if (e.status === 403) location.replace(restaurantURL("/meus-pedidos"));
    } finally { busy = false; }
  }
  if (balanceNode) {
    setInterval(refresh, 15000);
    window.addEventListener("orders-updated", refresh);
    window.addEventListener("online", refresh);
    document.addEventListener("visibilitychange", refresh);
  }
  const form = document.querySelector("#loyalty-checkout");
  if (!form) return;
  const mode = form.elements.modalidade, address = document.querySelector("#loyalty-address");
  const error = document.querySelector("#loyalty-error"), submit = form.querySelector("[type=submit]");
  let sending = false, pending = null;
  const key = restaurantURL("/") + "loyalty-pending-" + form.dataset.user;
  function update() {
    const delivery = mode.value === "entrega";
    address.hidden = !delivery;
    address.querySelectorAll("[data-required]").forEach(el => el.required = delivery);
    document.querySelector("#loyalty-payment").hidden = !delivery || Number(form.dataset.fee) === 0;
    document.querySelector("#loyalty-total").textContent = money(delivery ? Number(form.dataset.fee) : 0);
  }
  function lock(value) {
    [...form.elements].forEach(el => { if (el !== submit) el.disabled = value; });
  }
  function done(id) {
    try { sessionStorage.removeItem(key); } catch {}
    location.assign(restaurantURL("/meus-pedidos") + "?pedido=" + id);
  }
  try {
    pending = JSON.parse(sessionStorage.getItem(key) || "null");
    if (pending) {
      lock(true);
      error.hidden = false;
      error.textContent = "Há um resgate aguardando confirmação. Confira Meus pedidos ou reenvie a mesma tentativa.";
      api("/api/cliente/envios/" + encodeURIComponent(pending.chave)).then(data => { if (data.id) done(data.id); }).catch(() => {});
    }
  } catch { pending = null; }
  mode.onchange = update;
  form.onsubmit = async event => {
    event.preventDefault();
    if (sending) return;
    if (!pending) {
      if (!form.reportValidity()) return;
      pending = {
        chave: form.dataset.key, resgate_id: Number(form.dataset.reward),
        pontos_previstos: Number(form.dataset.points), modalidade: mode.value,
        forma_pagamento: form.elements.forma_pagamento.value,
        total_previsto: mode.value === "entrega" ? Number(form.dataset.fee) : 0
      };
      if (mode.value === "entrega")
        address.querySelectorAll("input").forEach(el => pending[el.name] = el.value.trim());
      try { sessionStorage.setItem(key, JSON.stringify(pending)); } catch {}
    }
    sending = true; submit.disabled = true; lock(true); error.hidden = true;
    try { const data = await api("/api/cliente/pedidos", pending); done(data.id); }
    catch (e) {
      error.textContent = e.message; error.hidden = false;
      if (e.status) {
        pending = null;
        try { sessionStorage.removeItem(key); } catch {}
        lock(false);
      } else error.textContent = "A resposta não chegou. Reenvie a mesma tentativa: ela não descontará os pontos duas vezes.";
    } finally { sending = false; submit.disabled = false; }
  };
  update();
})();
