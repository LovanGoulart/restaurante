"use strict";
let cart = [],
  sending = false;
const cartEl = document.querySelector("#cart"),
  send = document.querySelector("#send"),
  bag = document.querySelector("#bag"),
  mobileCart = document.querySelector("#mobile-cart");
function setBag(open) {
  document.body.classList.toggle("bag-open", open);
  document.querySelector("#bag-backdrop").hidden = !open;
  mobileCart.setAttribute("aria-expanded", String(open));
  if (open) {
    bag.setAttribute("role", "dialog");
    bag.setAttribute("aria-modal", "true");
    bag.setAttribute("aria-label", "Revisar pedido");
    document.querySelector(".bag-close").focus();
  } else {
    bag.removeAttribute("role");
    bag.removeAttribute("aria-modal");
    bag.removeAttribute("aria-label");
    mobileCart.focus();
  }
}
mobileCart.onclick = () => setBag(true);
document.querySelector(".bag-close").onclick = () => setBag(false);
document.querySelector("#bag-backdrop").onclick = () => setBag(false);
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && document.body.classList.contains("bag-open")) setBag(false);
  if (e.key === "Tab" && document.body.classList.contains("bag-open")) {
    const nodes = [
      ...bag.querySelectorAll("button:not(:disabled), input, textarea"),
    ].filter((el) => el.offsetParent !== null);
    if (e.shiftKey && document.activeElement === nodes[0]) {
      e.preventDefault();
      nodes.at(-1).focus();
    } else if (!e.shiftKey && document.activeElement === nodes.at(-1)) {
      e.preventDefault();
      nodes[0].focus();
    }
  }
});
window.matchMedia("(min-width:851px)").addEventListener("change", (e) => {
  if (e.matches) {
    bag.removeAttribute("role");
    bag.removeAttribute("aria-modal");
    bag.removeAttribute("aria-label");
    document.body.classList.remove("bag-open");
    document.querySelector("#bag-backdrop").hidden = true;
    mobileCart.setAttribute("aria-expanded", "false");
  }
});
function updateTotals() {
  const count = cart.reduce((n, i) => n + i.quantidade, 0),
    total = money(cart.reduce((n, i) => n + i.preco * i.quantidade, 0));
  document.querySelector("#total").textContent = total;
  document.querySelector("#mobile-total").textContent = total;
  document.querySelector("#cart-count").textContent = count;
  document.querySelector("#mobile-count").textContent = count;
  send.disabled = !cart.length || sending || !navigator.onLine;
  send.textContent = sending ? "Enviando pedido…" : "Enviar para a cozinha →";
}
function draw() {
  cartEl.innerHTML =
    cart
      .map(
        (i, k) => /* HTML */ `
          <div class="cart-item">
            <b>${escapeHTML(i.nome)}</b>
            <div class="quantity">
              <button
                data-change="-1"
                data-index="${k}"
                aria-label="Diminuir ${escapeHTML(i.nome)}"
              >
                −
              </button>
              <span>${i.quantidade}</span>
              <button
                data-change="1"
                data-index="${k}"
                aria-label="Aumentar ${escapeHTML(i.nome)}"
              >
                +
              </button>
              <strong>${money(i.preco * i.quantidade)}</strong>
            </div>
            <textarea
              data-note="${k}"
              maxlength="300"
              rows="1"
              placeholder="Observação (ex.: sem cebola)"
              aria-label="Observação para ${escapeHTML(i.nome)}"
            >
${escapeHTML(i.observacao)}</textarea>
          </div>
        `,
      )
      .join("") ||
    '<div class="empty"><span>🛍️</span><h3>O que vamos servir?</h3><p>Toque em + para adicionar um produto.</p></div>';
  updateTotals();
}
document.querySelectorAll(".add").forEach(
  (b) =>
    (b.onclick = () => {
      if (sending) return;
      let i = cart.find((i) => i.id === +b.dataset.id);
      if (i) {
        if (i.quantidade < 99) i.quantidade++;
      } else
        cart.push({
          id: +b.dataset.id,
          nome: b.dataset.name,
          preco: +b.dataset.price,
          quantidade: 1,
          observacao: "",
        });
      draw();
      b.textContent = "✓";
      setTimeout(() => (b.textContent = "+"), 650);
    }),
);
cartEl.onclick = (e) => {
  const b = e.target.closest("[data-change]");
  if (!b || sending) return;
  const k = +b.dataset.index;
  cart[k].quantidade = Math.min(99, cart[k].quantidade + +b.dataset.change);
  if (cart[k].quantidade <= 0) cart.splice(k, 1);
  draw();
};
cartEl.oninput = (e) => {
  if (e.target.dataset.note !== undefined)
    cart[+e.target.dataset.note].observacao = e.target.value;
};
let category = "all";
function filter() {
  const q = document.querySelector("#search").value.toLocaleLowerCase("pt-BR");
  let count = 0;
  document.querySelectorAll(".product").forEach((p) => {
    p.hidden =
      !(category === "all" || p.dataset.category === category) ||
      !p.dataset.name.includes(q);
    if (!p.hidden) count++;
  });
  document.querySelector("#empty-search").hidden = !!count;
}
document.querySelector("#search").oninput = filter;
document.querySelectorAll(".chip").forEach(
  (b) =>
    (b.onclick = () => {
      category = b.dataset.category;
      document.querySelectorAll(".chip").forEach((c) => {
        c.classList.toggle("active", c === b);
        c.setAttribute("aria-pressed", String(c === b));
      });
      filter();
    }),
);
send.onclick = async () => {
  if (sending) return;
  const mesa = document.querySelector("#mesa").value.trim();
  if (!mesa) {
    toast("Informe a mesa antes de enviar.");
    document.querySelector("#mesa").focus();
    return;
  }
  sending = true;
  updateTotals();
  try {
    const p = await api("/api/pedidos", {
      mesa,
      itens: cart.map(({ id, quantidade, observacao }) => ({
        id,
        quantidade,
        observacao,
      })),
    });
    cart = [];
    document.querySelector("#mesa").value = "";
    draw();
    if (document.body.classList.contains("bag-open")) setBag(false);
    toast("✓ Pedido #" + p.id + " enviado para a cozinha.\nMesa " + mesa);
  } catch (e) {
    toast(e.message + " Se houve falha de conexão, confira Pedidos antes de reenviar.");
  } finally {
    sending = false;
    updateTotals();
  }
};
window.addEventListener("offline", updateTotals);
window.addEventListener("online", updateTotals);
draw();
