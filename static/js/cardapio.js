"use strict";
const bag = document.querySelector("#bag"),
  cartEl = document.querySelector("#cart"),
  send = document.querySelector("#send"),
  mobileCart = document.querySelector("#mobile-cart"),
  mode = document.querySelector("#online-mode"),
  payment = document.querySelector("#online-payment");
let cart = [],
  sending = false,
  pending = null,
  category = "all";
const storageKey = restaurantURL("/") + "restaurant-online-cart",
  tokenKey = restaurantURL("/") + "restaurant-online-attempt";
const catalog = new Map(
  [...document.querySelectorAll(".add")].map((b) => [
    +b.dataset.id,
    { id: +b.dataset.id, nome: b.dataset.name, preco: +b.dataset.price },
  ]),
);
function save() {
  try {
    sessionStorage.setItem(
      storageKey,
      JSON.stringify({
        itens: cart.map(
          ({
            id,
            quantidade,
            observacao,
            opcoes,
            opcoes_versao,
            quantidade_sabores,
          }) => ({
            id,
            quantidade,
            observacao,
            opcoes,
            opcoes_versao,
            quantidade_sabores,
          }),
        ),
        modalidade: mode.value,
        pagamento: payment.value,
      }),
    );
  } catch {}
}
try {
  const data = JSON.parse(sessionStorage.getItem(storageKey) || "null");
  if (data && Array.isArray(data.itens)) {
    cart = data.itens
      .slice(0, 100)
      .map((i) => ProductPicker.restore(i))
      .filter(Boolean);
    if (cart.length !== data.itens.length)
      toast(
        "Alguns itens mudaram. Confira o cardápio e escolha as opções novamente.",
      );
    if ([...mode.options].some((o) => o.value === data.modalidade))
      mode.value = data.modalidade;
    if ([...payment.options].some((o) => o.value === data.pagamento))
      payment.value = data.pagamento;
  }
} catch {}
function setBag(open) {
  document.body.classList.toggle("bag-open", open);
  document.querySelector("#bag-backdrop").hidden = !open;
  mobileCart.setAttribute("aria-expanded", String(open));
  if (open) {
    bag.setAttribute("role", "dialog");
    bag.setAttribute("aria-modal", "true");
    bag.setAttribute("aria-label", "Sua sacola e finalização");
    document.querySelector(".bag-close").focus();
  } else {
    bag.removeAttribute("role");
    bag.removeAttribute("aria-modal");
    document.querySelector("#bag-backdrop").hidden = true;
    mobileCart.focus();
  }
}
mobileCart.onclick = () => setBag(true);
document.querySelector(".bag-close").onclick = () => setBag(false);
document.querySelector("#bag-backdrop").onclick = () => setBag(false);
window.addEventListener("keydown", (e) => {
  if (
    !document.querySelector("#product-picker").open &&
    e.key === "Escape" &&
    document.body.classList.contains("bag-open")
  )
    setBag(false);
  if (
    !document.querySelector("#product-picker").open &&
    e.key === "Tab" &&
    document.body.classList.contains("bag-open")
  ) {
    const nodes = [
      ...bag.querySelectorAll(
        "button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), a",
      ),
    ].filter((n) => n.offsetParent !== null);
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
    document.body.classList.remove("bag-open");
    document.querySelector("#bag-backdrop").hidden = true;
    bag.removeAttribute("role");
    bag.removeAttribute("aria-modal");
  }
});
function totals() {
  const subtotal = cart.reduce((sum, i) => sum + i.preco * i.quantidade, 0),
    fee = mode.value === "entrega" ? Number(bag.dataset.fee) : 0,
    count = cart.reduce((sum, i) => sum + i.quantidade, 0);
  document.querySelector("#subtotal").textContent = money(subtotal);
  document.querySelector("#delivery-fee").textContent = money(fee);
  document.querySelector("#total").textContent = money(subtotal + fee);
  document.querySelector("#mobile-total").textContent = money(subtotal + fee);
  document.querySelector("#mobile-count").textContent = count;
  document.querySelector("#cart-count").textContent = count;
  if (send) {
    send.disabled =
      !cart.length ||
      sending ||
      !navigator.onLine ||
      bag.dataset.active !== "yes";
    send.textContent = sending
      ? "Enviando pedido…"
      : pending
        ? "Reenviar a mesma tentativa →"
        : bag.dataset.customer === "yes"
          ? "Confirmar meu pedido →"
          : "Entrar para fazer o pedido →";
  }
  return subtotal + fee;
}
function draw() {
  cartEl.innerHTML =
    cart.map((i, k) => ProductPicker.line(i, k)).join("") ||
    '<p class="empty">Sua sacola está vazia.<br>Escolha algo gostoso no cardápio.</p>';
  totals();
  save();
}
function lock(value) {
  bag
    .querySelectorAll(
      ".checkout-details input,.checkout-details select,#cart button,#cart textarea",
    )
    .forEach((e) => (e.disabled = value));
}
ProductPicker.bind({
  canEdit: () => !sending && !pending,
  onAdd: (item) => {
    const items = Array.isArray(item) ? item : [item];
    if (cart.length + items.length > 100) {
      toast("Use até 100 linhas por envio.");
      return false;
    }
    cart.push(...items);
    draw();
    toast(
      items.length > 1
        ? "Pizzas adicionadas separadamente ao pedido."
        : "Item adicionado ao pedido.",
    );
    return true;
  },
});
cartEl.onclick = (e) => {
  if (sending || pending) return;
  const edit = e.target.closest("[data-edit]");
  if (edit && !sending && !pending) {
    const index = +edit.dataset.edit;
    ProductPicker.edit(cart[index], (item) => {
      const items = Array.isArray(item) ? item : [item];
      if (cart.length - 1 + items.length > 100) {
        toast("Use até 100 linhas por envio.");
        return false;
      }
      cart.splice(index, 1, ...items);
      draw();
      return true;
    });
    return;
  }
  const b = e.target.closest("[data-change]");
  if (!b) return;
  const k = +b.dataset.index;
  if (
    +b.dataset.change === 1 &&
    cart[k].quantidade < 99 &&
    ProductPicker.isPizza(cart[k])
  ) {
    ProductPicker.edit(
      {
        ...cart[k],
        quantidade: cart[k].quantidade + 1,
        quantidade_original: cart[k].quantidade,
      },
      (item) => {
        const items = Array.isArray(item) ? item : [item];
        if (cart.length - 1 + items.length > 100) {
          toast("Use até 100 linhas por envio.");
          return false;
        }
        cart.splice(k, 1, ...items);
        draw();
        return true;
      },
    );
    return;
  }
  cart[k].quantidade = Math.min(99, cart[k].quantidade + +b.dataset.change);
  if (cart[k].quantidade <= 0) cart.splice(k, 1);
  draw();
};
cartEl.oninput = (e) => {
  if (e.target.dataset.note !== undefined) {
    cart[+e.target.dataset.note].observacao = e.target.value;
    save();
  }
};
function checkout() {
  const delivery = mode.value === "entrega",
    fields = document.querySelector("#checkout-address");
  fields.hidden = !delivery;
  fields
    .querySelectorAll("input")
    .forEach(
      (input) => (input.required = delivery && input.name !== "telefone"),
    );
  document.querySelector("#change-label").hidden = payment.value !== "dinheiro";
  totals();
  save();
}
mode.onchange = checkout;
payment.onchange = checkout;
function token() {
  try {
    let t = sessionStorage.getItem(tokenKey);
    if (t) return t;
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    t = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    sessionStorage.setItem(tokenKey, t);
    return t;
  } catch {
    return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) =>
      b.toString(16).padStart(2, "0"),
    ).join("");
  }
}
function done(id) {
  cart = [];
  pending = null;
  try {
    sessionStorage.removeItem(storageKey);
    sessionStorage.removeItem(tokenKey);
  } catch {}
  toast("Pedido #" + id + " recebido!");
  window.location.assign(restaurantURL("/meus-pedidos"));
}
if (send)
  send.onclick = async () => {
    if (sending) return;
    if (bag.dataset.customer !== "yes") {
      save();
      window.location.assign(restaurantURL("/login"));
      return;
    }
    if (!pending) {
      const payload = {
        chave: token(),
        modalidade: mode.value,
        forma_pagamento: payment.value,
        troco_para:
          payment.value === "dinheiro"
            ? document.querySelector("#change-for").value
            : "",
        total_previsto: totals(),
        itens: cart.map(
          ({
            id,
            quantidade,
            observacao,
            opcoes,
            opcoes_versao,
            quantidade_sabores,
          }) => ({
            id,
            quantidade,
            observacao,
            opcoes,
            opcoes_versao,
            quantidade_sabores,
          }),
        ),
      };
      if (mode.value === "entrega") {
        const fields = [
          ...document.querySelectorAll("#checkout-address input"),
        ];
        for (const input of fields) {
          if (!input.checkValidity()) {
            input.reportValidity();
            return;
          }
          payload[input.name] = input.value.trim();
        }
      }
      pending = payload;
    }
    sending = true;
    lock(true);
    totals();
    try {
      const result = await api("/api/cliente/pedidos", pending);
      done(result.id);
    } catch (e) {
      if (e.status) {
        pending = null;
        lock(false);
        toast(e.message);
      } else {
        toast(
          "Não foi possível confirmar a resposta. Você pode reenviar a mesma tentativa com segurança ou conferir Meus pedidos.",
        );
      }
    } finally {
      sending = false;
      totals();
    }
  };
window.addEventListener("offline", totals);
window.addEventListener("online", totals);
draw();
checkout();
if (bag.dataset.customer === "yes") {
  try {
    const savedToken = sessionStorage.getItem(tokenKey);
    if (savedToken)
      api("/api/cliente/envios/" + encodeURIComponent(savedToken))
        .then((result) => {
          if (result.id) done(result.id);
        })
        .catch(() => {});
  } catch {}
}
