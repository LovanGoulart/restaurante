(() => {
  const root = document.getElementById("fiscal-app");
  if (!root) return;
  const form = document.getElementById("fiscal-config");
  const base = root.dataset.base;
  const cnpj = form.elements.cnpj;
  const formatCnpj = () => {
    const value = cnpj.value
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, "")
      .slice(0, 14);
    cnpj.value = [...value]
      .map(
        (character, index) =>
          (({ 2: ".", 5: ".", 8: "/", 12: "-" })[index] || "") + character,
      )
      .join("");
  };
  cnpj.addEventListener("input", formatCnpj);
  formatCnpj();
  async function post(path, body, result, button) {
    const old = button?.textContent;
    if (button) {
      button.disabled = true;
      button.textContent = "Aguarde…";
    }
    result.className = "";
    result.textContent = "Processando…";
    try {
      const headers = { "X-CSRF-Token": root.dataset.csrf };
      if (!(body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(body);
      }
      const response = await fetch(base + path, {
        method: "POST",
        headers,
        body,
      });
      const type = response.headers.get("Content-Type") || "";
      const data = type.includes("application/json")
        ? await response.json()
        : {};
      if (!response.ok)
        throw new Error(
          data.error ||
            "Acesso expirado ou operação indisponível. Reabra a área fiscal pelo menu e confira sua senha.",
        );
      result.className = "fiscal-success";
      result.textContent = data.message || "Operação concluída.";
      return true;
    } catch (error) {
      result.className = "fiscal-error";
      result.textContent =
        error.message || "Não foi possível concluir a operação.";
      return false;
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = old;
      }
    }
  }
  document.getElementById("fiscal-test").onclick = (event) => {
    const body = new FormData(form);
    // O teste de token não precisa transferir arquivo ou senha do certificado.
    body.delete("certificado");
    body.delete("senha_certificado");
    post(
      "/testar",
      body,
      document.getElementById("fiscal-test-result"),
      event.currentTarget,
    );
  };
  form.onsubmit = async (event) => {
    event.preventDefault();
    const result = document.getElementById("fiscal-config-result");
    if (
      await post(
        "/configurar",
        new FormData(form),
        result,
        form.querySelector("[type=submit]"),
      )
    ) {
      form.elements.token.value = "";
      form.elements.master.value = "";
      form.elements.senha_certificado.value = "";
      form.elements.certificado.value = "";
      // Recarregar atualiza a série, o número e o botão do certificado.
      result.append(" Recarregue a página para exibir os dados atualizados.");
    }
  };
  document.getElementById("fiscal-certificate-send").onclick = (event) => {
    if (
      confirm(
        "Enviar o certificado salvo à Focus NFe? Ele será usado pela empresa cadastrada também em produção.",
      )
    )
      post(
        "/certificado/enviar",
        {},
        document.getElementById("fiscal-config-result"),
        event.currentTarget,
      );
  };
  const ruleForm = document.getElementById("fiscal-rule-form");
  ruleForm.onsubmit = (event) => {
    event.preventDefault();
    const fields = Object.fromEntries(new FormData(ruleForm));
    const name = fields.nome_item;
    delete fields.nome_item;
    post(
      "/regras",
      { nome_item: name, campos: fields },
      document.getElementById("fiscal-rule-result"),
      ruleForm.querySelector("[type=submit]"),
    );
  };
  const rules = JSON.parse(
    document.getElementById("fiscal-rules-values").textContent,
  );
  root.querySelectorAll("[data-edit-rule]").forEach((button) => {
    button.onclick = () => {
      const rule = rules.find((r) => r.id === Number(button.dataset.editRule));
      ruleForm.reset();
      ruleForm.elements.nome_item.value = rule.nome_item;
      for (const [key, value] of Object.entries(rule.campos))
        if (ruleForm.elements[key]) ruleForm.elements[key].value = value;
      ruleForm.scrollIntoView({ behavior: "smooth", block: "center" });
    };
  });
  const manual = document.getElementById("fiscal-manual");
  manual.onsubmit = (event) => {
    event.preventDefault();
    post(
      "/pedidos/" +
        encodeURIComponent(manual.elements.pedido.value) +
        "/emitir",
      {},
      document.getElementById("fiscal-manual-result"),
      manual.querySelector("[type=submit]"),
    );
  };
  const recipient = document.getElementById("fiscal-recipient");
  recipient.onsubmit = (event) => {
    event.preventDefault();
    post(
      "/notas/" +
        encodeURIComponent(recipient.elements.nota.value) +
        "/destinatario",
      new FormData(recipient),
      document.getElementById("fiscal-recipient-result"),
      recipient.querySelector("[type=submit]"),
    );
  };
  root.querySelectorAll("[data-note-action]").forEach((button) => {
    button.onclick = () =>
      post(
        "/notas/" + button.dataset.noteId + "/" + button.dataset.noteAction,
        {},
        document.getElementById("fiscal-note-result"),
        button,
      );
  });
})();
