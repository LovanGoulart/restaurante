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
    cart.map((i, k) => ProductPicker.line(i, k)).join("") ||
    '<div class="empty"><span>🛍️</span><h3>O que vamos servir?</h3><p>Toque em + para adicionar um produto.</p></div>';
  updateTotals();
}
ProductPicker.bind({
  canEdit: () => !sending,
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
  const edit = e.target.closest("[data-edit]");
  if (edit && !sending) {
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
  if (!b || sending) return;
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
  if (e.target.dataset.note !== undefined)
    cart[+e.target.dataset.note].observacao = e.target.value;
};
let pendingKey = crypto.randomUUID().replaceAll("-", "");
send.onclick = async () => {
  if (sending) return;
  const qr = bag.dataset.qr === "yes";
  const comanda = document.querySelector("#comanda")?.value.trim();
  const numero_mesa = document.querySelector("#numero-mesa")?.value.trim();
  if (
    !qr &&
    (!/^\d{1,12}$/.test(comanda || "") || !/^\d{1,12}$/.test(numero_mesa || ""))
  ) {
    toast("Informe os números da comanda e da mesa.");
    return;
  }
  sending = true;
  updateTotals();
  try {
    const p = await api(qr ? "/api/salao/pedidos" : "/api/pedidos", {
      comanda,
      numero_mesa,
      chave: pendingKey,
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
    });
    cart = [];
    pendingKey = crypto.randomUUID().replaceAll("-", "");
    draw();
    if (document.body.classList.contains("bag-open")) setBag(false);
    toast(
      qr
        ? "Pedido enviado! Acompanhe em Meus pedidos."
        : (p.adicionado
            ? "Itens adicionados à comanda "
            : "Pedido enviado. Comanda ") +
            comanda +
            " · Mesa " +
            numero_mesa,
    );
    if (qr) location.assign(restaurantURL("/salao/meus-pedidos"));
  } catch (e) {
    toast(
      e.message +
        " Se houve falha de conexão, confira Pedidos antes de reenviar.",
    );
  } finally {
    sending = false;
    updateTotals();
  }
};
window.addEventListener("offline", updateTotals);
window.addEventListener("online", updateTotals);
draw();

const existing = new URLSearchParams(location.search).get("pedido");
if (existing && bag.dataset.qr !== "yes")
  api("/api/pedidos/" + Number(existing) + "/detalhes")
    .then((p) => {
      if (p.canal !== "salao" || p.pago)
        throw new Error("Comanda indisponível para adicionar itens.");
      document.querySelector("#comanda").value = p.comanda;
      document.querySelector("#numero-mesa").value = p.numero_mesa;
      toast("Adicionando itens à comanda " + p.comanda);
    })
    .catch((e) => toast(e.message));
