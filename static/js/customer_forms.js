"use strict";
const mode = document.querySelector("#registration-mode"),
  address = document.querySelector("#registration-address");
function showAddress() {
  const delivery = mode.value === "entrega";
  address.hidden = !delivery;
  address.querySelectorAll("input").forEach((input) => {
    input.required = delivery && input.name !== "telefone";
    input.disabled = !delivery;
  });
}
mode?.addEventListener("change", showAddress);
if (mode) showAddress();
