"use strict";
(() => {
  const date = document.querySelector("#settlement-date"),
    driver = document.querySelector("#settlement-driver"),
    root = document.querySelector("#settlement-items"),
    open = document.querySelector("#settlement-open"),
    dialog = document.querySelector("#settlement-dialog"),
    error = document.querySelector("#settlement-error");
  const confirmation = document.querySelector("#settlement-confirm-check");
  const confirmButton = document.querySelector("#settlement-confirm");
  const syncConfirmation = () => {
    confirmButton.disabled = !confirmation.checked || busy;
  };
  confirmation.addEventListener("change", syncConfirmation);
  let items = [],
    ids = [],
    busy = false,
    loading = false,
    pending = false;
  const forms = {
    dinheiro: "Dinheiro",
    pix: "Pix",
    credito: "Crédito",
    debito: "Débito",
    antecipado: "Antecipado",
  };
  date.value = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  function chosen() {
    return [...root.querySelectorAll("[data-select]:checked")].map((e) =>
      Number(e.dataset.select),
    );
  }
  function update() {
    open.disabled = !chosen().length;
    const checks = [...root.querySelectorAll("[data-select]")],
      all = document.querySelector("#settlement-all");
    all.checked = !!checks.length && checks.every((c) => c.checked);
    all.indeterminate = checks.some((c) => c.checked) && !all.checked;
  }
  async function refresh() {
    if (busy || loading || dialog.open) {
      pending = true;
      return;
    }
    loading = true;
    try {
      const data = await api(
        "/api/acerto-entregadores?data=" +
          date.value +
          "&entregador_id=" +
          driver.value,
      );
      items = data.items;
      const saved = driver.value;
      driver.innerHTML =
        '<option value="">Todos</option>' +
        data.entregadores
          .map(
            (u) => /* HTML */ `
              <option value="${u.id}">${escapeHTML(u.nome)}</option>
            `,
          )
          .join("");
      driver.value = saved;
      document.querySelector("#settlement-summary").innerHTML =
        data.resumo
          .map(
            (r) => /* HTML */ `
              <section class="panel">
                <h2>${escapeHTML(r.nome)}</h2>
                <p>${r.entregas} entrega(s) · ${money(r.total_pedidos)} em pedidos</p>
                <div class="courier-cash">
                  <span>Dinheiro a repassar</span>
                  <strong>${money(r.dinheiro_repassar)}</strong>
                </div>
                <div class="fee-line">
                  <span>Pix a conferir</span>
                  <b>${money(r.formas.pix)}</b>
                </div>
                <div class="fee-line">
                  <span>Crédito a conferir</span>
                  <b>${money(r.formas.credito)}</b>
                </div>
                <div class="fee-line">
                  <span>Débito a conferir</span>
                  <b>${money(r.formas.debito)}</b>
                </div>
                <div class="fee-line">
                  <span>Total recebido nas entregas</span>
                  <b>${money(r.recebido_total)}</b>
                </div>
                <div class="fee-line">
                  <span>Recebimentos já conferidos</span>
                  <b>${money(r.conferido)}</b>
                </div>
                <div class="fee-line">
                  <span>Pagos antecipadamente</span>
                  <b>${money(r.antecipado)}</b>
                </div>
                <p class="muted">
                  ${r.pendentes} entrega(s) pendente(s) de conferência ·
                  ${money(r.a_conferir)} em recebimentos a conferir.
                </p>
              </section>
            `,
          )
          .join("") ||
        '<section class="panel">Nenhuma entrega concluída neste filtro.</section>';
      const selectedIds = new Set(chosen());
      root.innerHTML =
        items
          .map(
            (e) => /* HTML */ `
              <div class="settlement-row">
                <label class="check">
                  ${!e.acertado ? `<input type="checkbox" data-select="${e.id}" ${selectedIds.has(e.id) ? "checked" : ""} aria-label="Conferir pedido ${e.pedido_id}">` : "<span>✓</span>"}
                  <span>
                    <b>Pedido #${e.pedido_id} · ${escapeHTML(e.cliente)}</b>
                    <small>
                      ${escapeHTML(e.entregador)} ·
                      ${new Date(e.entregue_em).toLocaleString("pt-BR")}
                    </small>
                  </span>
                </label>
                <div>
                  <b>${money(e.valor_pedido)}</b>
                  <small>
                    ${forms[e.forma_pagamento]}${e.pago_antecipado ? " · já pago antes da entrega" : " · " + money(e.valor_recebido) + " recebido"}
                  </small>
                  <small>
                    ${e.acertado ? "Acerto conferido" : "Pendente de conferência"}
                  </small>
                </div>
              </div>
            `,
          )
          .join("") || "<p>Sem entregas para exibir.</p>";
      error.hidden = true;
      update();
    } catch (e) {
      error.textContent = e.message;
      error.hidden = false;
    } finally {
      loading = false;
      if (pending) {
        pending = false;
        setTimeout(refresh, 50);
      }
    }
  }
  root.onchange = update;
  document.querySelector("#settlement-all").onchange = (e) => {
    root
      .querySelectorAll("[data-select]")
      .forEach((c) => (c.checked = e.target.checked));
    update();
  };
  open.onclick = () => {
    ids = chosen();
    const selected = items.filter((e) => ids.includes(e.id)),
      cash = selected
        .filter((e) => e.forma_pagamento === "dinheiro")
        .reduce((s, e) => s + e.valor_recebido, 0),
      total = selected.reduce((s, e) => s + e.valor_recebido, 0);
    document.querySelector("#settlement-confirm-summary").textContent =
      selected.length +
      " entrega(s) · " +
      money(cash) +
      " em dinheiro a repassar · " +
      money(total - cash) +
      " em pagamentos eletrônicos a conferir.";
    document.querySelector("#settlement-confirm-check").checked = false;
    syncConfirmation();
    dialog.showModal();
  };
  document.querySelector("#settlement-confirm").onclick = async (e) => {
    if (!document.querySelector("#settlement-confirm-check").checked) {
      toast("Confirme que recebeu o dinheiro e conferiu os pagamentos.");
      return;
    }
    busy = true;
    e.target.disabled = true;
    try {
      await api("/api/acerto-entregadores", { entregas: ids, confirmado: true });
      dialog.close();
      toast("Acerto registrado no caixa.");
    } catch (err) {
      toast(err.message);
    } finally {
      busy = false;
      syncConfirmation();
      refresh();
    }
  };
  dialog.addEventListener("close", () => {
    if (pending && !busy) refresh();
  });
  syncConfirmation();
  date.onchange = refresh;
  driver.onchange = refresh;
  document.querySelector("#settlement-refresh").onclick = refresh;
  window.addEventListener("orders-updated", refresh);
  setInterval(() => {
    if (document.visibilityState === "visible" && !dialog.open) refresh();
  }, 30000);
  refresh();
})();
