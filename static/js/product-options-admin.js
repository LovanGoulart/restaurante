"use strict";
(() => {
  const form = document.querySelector("#options-config"),
    container = document.querySelector("#options-groups"),
    data = JSON.parse(document.querySelector("#options-config-data").textContent);
  form.noValidate = true;
  let version = data.version, saving = false;
  const groups = data.config.groups, opened = new Set(), message = document.querySelector("#options-message");
  const uid = () => crypto.randomUUID().replaceAll("-", ""), safe = escapeHTML;
  const check = value => value ? "checked" : "";
  const normalize = s => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const moneyInput = c => c.amount ?? (c.price / 100).toFixed(2).replace(".", ",");
  const kind = g => g.type === "sizes" ? "sizes" : g.type === "flavors" ? "flavors" : /borda/.test(normalize(g.title)) ? "border" : /massa/.test(normalize(g.title)) ? "dough" : /ponto.*carne|carne.*ponto/.test(normalize(g.title)) ? "meat" : "custom";
  const blocks = {
    sizes: ["Tamanhos de pizza", "Defina o nome, as fatias, o limite de sabores e o acréscimo de cada tamanho.", "▦", "Adicionar tamanho"],
    flavors: ["Sabores da pizza", "Informe o preço inteiro de cada sabor. O pedido calcula a média dos sabores escolhidos.", "◔", "Adicionar sabor"],
    border: ["Bordas", "Cadastre as bordas disponíveis e quanto cada uma acrescenta à pizza.", "◎", "Adicionar borda"],
    dough: ["Massas", "Defina as massas que o cliente pode escolher e seus acréscimos.", "≋", "Adicionar massa"],
    meat: ["Ponto da carne", "Ofereça opções como mal passado, ao ponto e bem passado.", "♨", "Adicionar ponto"],
    custom: ["Outro bloco de opções", "Use para adicionais, acompanhamentos ou outra escolha do seu produto.", "+", "Adicionar opção"],
  };
  function sizeParts(c) {
    const match = c.label.match(/^(.*?)\s*(?:[·•–—-]\s*)?(\d+)\s*fatias?$/i);
    return {name: match ? match[1].replace(/[·•–—-]\s*$/, "").trim() : c.label, slices: match ? match[2] : ""};
  }
  function choice(label = "", extra = {}) { return {id: uid(), label, price: 0, amount: "0,00", enabled: true, ...extra}; }
  function group(type, title, choices = []) { return {id: uid(), title, enabled: true, required: true, type, max: type === "flavors" ? 20 : 1, choices}; }
  groups.forEach(g => g.choices.forEach(c => c.amount = moneyInput(c)));
  if (groups[0]) opened.add(groups[0].id);
  document.querySelector("#notes-enabled").checked = data.config.notes.enabled;
  document.querySelector("#notes-label").value = data.config.notes.label;
  document.querySelector("#notes-placeholder").value = data.config.notes.placeholder;
  function show(text, failure = false) {
    message.textContent = text; message.hidden = false; message.className = failure ? "error" : "success";
    if (failure) message.scrollIntoView({block: "nearest", behavior: "smooth"});
  }
  function summary() {
    let warning = document.querySelector("#oe-flavor-capacity");
    if (!warning) { warning = document.createElement("p"); warning.id="oe-flavor-capacity";warning.className="oe-tip";warning.setAttribute("role","status");container.before(warning); }
    const sizes = groups.filter(g=>g.enabled&&g.type==="sizes"), flavors = groups.filter(g=>g.enabled&&g.type==="flavors");
    const available = data.pizzaMenu ? data.flavorCount : flavors.reduce((n,g)=>n+g.choices.filter(c=>c.enabled).length,0);
    const maximum = data.pizzaMenu ? Math.max(0,...[...document.querySelectorAll("[data-size-config]")].filter(row=>row.querySelector("[data-size-enabled]").checked).map(row=>Number(row.querySelector("[data-size-limit]").value))) : Math.max(0,...sizes.flatMap(g=>g.choices.filter(c=>c.enabled).map(c=>Number(c.max_flavors||1))));
    warning.hidden = !maximum || available >= maximum;
    warning.textContent = `Você definiu tamanhos com até ${maximum} sabores, mas cadastrou ${available} ${available === 1 ? "sabor visível" : "sabores visíveis"}. Para permitir essa variedade, ${data.pizzaMenu ? "cadastre mais produtos ativos nesta categoria de pizzas." : "adicione mais sabores no bloco Sabores da pizza."} O máximo por tamanho foi mantido.`;
    document.querySelector("#options-overview").textContent = `${groups.length} ${groups.length === 1 ? "bloco" : "blocos"} · ${groups.reduce((n,g) => n + (g.enabled ? g.choices.filter(c => c.enabled).length : 0), 0)} opções visíveis`;
  }
  function row(g, c, index) {
    const k = kind(g), size = sizeParts(c), noun = k === "sizes" ? "tamanho" : k === "flavors" ? "sabor" : k === "border" ? "borda" : "opção";
    return `<div class="oe-choice ${k === "sizes" ? "oe-size" : ""}" data-choice="${c.id}">
      <label>${k === "sizes" ? "Tamanho" : k === "flavors" ? "Nome do sabor" : k === "border" ? "Nome da borda" : "Nome da opção"}<input data-choice-field="${k === "sizes" ? "size_name" : "label"}" value="${safe(k === "sizes" ? size.name : c.label)}" placeholder="${k === "sizes" ? "Ex.: Média" : k === "flavors" ? "Ex.: Calabresa" : "Nome"}" maxlength="60" aria-label="Nome do ${noun} ${index + 1}"></label>
      ${k === "sizes" ? `<label>Fatias<input data-choice-field="slices" inputmode="numeric" value="${safe(size.slices)}" placeholder="Ex.: 8" maxlength="3" aria-label="Fatias do tamanho ${index + 1}"></label><label>Máx. sabores<input type="number" data-choice-field="max_flavors" min="1" max="20" value="${c.max_flavors || 1}" aria-label="Máximo de sabores do tamanho ${index + 1}"></label>` : ""}
      <label>${k === "flavors" ? "Preço inteiro (R$)" : "Acréscimo (R$)"}<input data-choice-field="amount" inputmode="decimal" value="${safe(moneyInput(c))}" placeholder="0,00" aria-label="${k === "flavors" ? "Preço" : "Acréscimo"} do ${noun} ${index + 1}"></label>
      <label class="check oe-visibility"><input data-choice-field="enabled" type="checkbox" ${check(c.enabled)}> Exibir</label><button type="button" class="oe-remove" data-remove-choice="${c.id}" aria-label="Remover ${noun} ${index + 1}" title="Remover ${noun}">×</button>${k !== "sizes" ? `<label class="oe-description">${k === "flavors" ? "Ingredientes / descrição do sabor" : "Descrição da opção (opcional)"}<textarea data-choice-field="description" rows="2" maxlength="400" placeholder="${k === "flavors" ? "Ex.: molho de tomate, muçarela, calabresa e cebola" : "Descreva esta opção"}" aria-label="Descrição do ${noun} ${index + 1}">${safe(c.description || "")}</textarea></label>` : ""}</div>`;
  }
  function render(focusId) {
    container.innerHTML = groups.map(g => {
      const k = kind(g), [title, help, icon, add] = blocks[k], pizza = ["sizes", "flavors"].includes(g.type);
      const titleShown = k === "custom" ? g.title : title;
      return `<details class="oe-block oe-${k}" data-group="${g.id}" ${opened.has(g.id) ? "open" : ""}>
        <summary><span class="oe-icon" aria-hidden="true">${icon}</span><span class="oe-block-caption"><strong>${safe(titleShown)}</strong><small>${g.choices.filter(c=>c.enabled).length} opções · ${g.enabled ? "Ativo" : "Oculto"}</small></span><span class="oe-chevron" aria-hidden="true">⌄</span></summary>
        <div class="oe-block-body"><p class="oe-help">${help}</p>
        <div class="oe-settings"><label class="check"><input type="checkbox" data-field="enabled" ${check(g.enabled)}> Exibir no cardápio</label>${pizza ? '<span class="oe-rule">Escolha obrigatória na montagem da pizza</span>' : `<label class="check"><input type="checkbox" data-field="required" ${check(g.required)}> Cliente precisa escolher</label>`}</div>
        ${!pizza ? `<div class="oe-custom-settings"><label>Nome do bloco no cardápio<input data-field="title" value="${safe(g.title)}" maxlength="48" placeholder="Ex.: Adicionais"></label><label>Como o cliente responde?<select data-field="type"><option value="single" ${g.type === "single" ? "selected" : ""}>Escolhe uma opção</option><option value="multiple" ${g.type === "multiple" ? "selected" : ""}>Pode escolher várias opções</option><option value="text" ${g.type === "text" ? "selected" : ""}>Escreve um texto curto</option></select></label>${g.type === "multiple" ? `<label>Máximo de opções<input type="number" min="1" max="20" data-field="max" value="${g.max}"></label>` : ""}</div>` : `<details class="oe-advanced"><summary>Alterar título exibido no cardápio</summary><label>Título<input data-field="title" value="${safe(g.title)}" maxlength="48"></label></details>`}
        ${k === "sizes" ? `<div class="oe-size-presets"><span>Incluir tamanho:</span>${["Broto", "Média", "Grande", "Família"].map((name,i)=>`<button type="button" class="secondary" data-size-preset="${i}">${name}</button>`).join("")}</div>` : ""}
        ${g.type === "text" ? '<p class="oe-tip">O cliente poderá escrever até 60 caracteres. Essa resposta não altera o preço.</p>' : `<div class="oe-choices">${g.choices.map((c,i)=>row(g,c,i)).join("") || '<p class="oe-empty">Nenhuma opção cadastrada. Use o botão abaixo para adicionar.</p>'}</div><button type="button" class="secondary oe-add" data-add-choice="${g.id}">+ ${add}</button><p class="oe-tip">${k === "flavors" ? "Ex.: sabores de R$ 50,00 e R$ 70,00 resultam em R$ 60,00, antes do tamanho e dos extras." : k === "sizes" ? "O acréscimo do tamanho soma à média dos sabores. As fatias aparecem junto ao nome. Use 0,00 se não houver acréscimo." : "Use 0,00 para opções sem custo adicional."}</p>`}
        <div class="oe-block-bottom"><small>Ocultar preserva a opção para usar depois.</small><button type="button" class="oe-delete-block" data-remove-group="${g.id}">${pizza ? "Remover montagem de pizza" : "Remover este bloco"}</button></div></div></details>`;
    }).join("") || '<div class="oe-empty-panel"><strong>Este produto ainda não tem opções.</strong><p>Escolha um dos blocos acima para começar. A observação livre pode ser usada sozinha.</p></div>';
    container.querySelectorAll("details[data-group]").forEach(el => el.addEventListener("toggle", () => { if(el.open) opened.add(el.dataset.group); else opened.delete(el.dataset.group); }));
    summary();
    if(focusId) requestAnimationFrame(() => {
      const block = container.querySelector(`[data-group="${focusId}"]`); block?.scrollIntoView({block:"nearest",behavior:"smooth"});
      block?.querySelector(".oe-choice:last-child input")?.focus();
    });
  }
  function ensurePreset(preset) {
    const typeFor = {pizza:"sizes",flavors:"flavors"}, existing = groups.find(g => typeFor[preset] ? g.type === typeFor[preset] : kind(g) === ({border:"border",meat:"meat",dough:"dough"}[preset]));
    if(existing && preset !== "custom") {opened.add(existing.id);render(existing.id);return;}
    const needed = ["pizza","flavors"].includes(preset) ? ["sizes","flavors"].filter(t=>!groups.some(g=>g.type===t)) : [preset];
    if(groups.length + needed.length > (data.pizzaMenu ? 6 : 8)){show(data.pizzaMenu ? "Use até seis blocos de massa, borda e acompanhamentos." : "O produto pode ter até oito blocos. Remova um bloco antes de adicionar outro.",true);return;}
    let target;
    for(const t of needed) {
      const g = t === "sizes" ? group("sizes","Tamanho e fatias") : t === "flavors" ? group("flavors","Sabores") : t === "border" ? group("single","Bordas",[choice("Sem borda")]) : t === "meat" ? group("single","Ponto da carne",[choice("Mal passado"),choice("Ao ponto"),choice("Bem passado")]) : t === "dough" ? group("single","Massas",[choice("Tradicional"),choice("Fina")]) : group("single","Adicionais");
      groups.push(g);opened.add(g.id);if(t === (typeFor[preset] || preset))target=g;
    }
    render(target?.id || groups.at(-1).id);
  }
  document.querySelectorAll("[data-preset]").forEach(b=>b.onclick=()=>{if(!saving)ensurePreset(b.dataset.preset);});
  container.addEventListener("input", e => {
    const field=e.target, g=groups.find(g=>g.id===field.closest("[data-group]")?.dataset.group);if(!g)return;
    const value=field.type==="checkbox"?field.checked:field.type==="number"?Number(field.value):field.value;
    if(field.dataset.field)g[field.dataset.field]=value;
    if(field.dataset.choiceField){
      const c=g.choices.find(c=>c.id===field.closest("[data-choice]").dataset.choice), key=field.dataset.choiceField;
      if(["size_name","slices"].includes(key)){
        const row=field.closest("[data-choice]"), name=row.querySelector('[data-choice-field="size_name"]').value, slices=row.querySelector('[data-choice-field="slices"]').value;
        c.label=name.trim()+(slices.trim()?" · "+slices.trim()+" fatias":"");
      } else c[key]=value;
    }
    field.removeAttribute("aria-invalid");
    summary();
  });
  container.addEventListener("change", e=>{
    const g=groups.find(g=>g.id===e.target.closest("[data-group]")?.dataset.group);if(!g)return;
    if(e.target.dataset.field==="type") {g.type=e.target.value;if(g.type!=="text"&&!g.choices.length)g.choices.push(choice());opened.add(g.id);render();}
    if(e.target.dataset.field==="enabled"&&["sizes","flavors"].includes(g.type)) {groups.filter(x=>["sizes","flavors"].includes(x.type)).forEach(x=>x.enabled=g.enabled);render();}
  });
  container.addEventListener("click",e=>{
    const b=e.target.closest("button");if(!b||saving)return;
    const g=groups.find(g=>g.id===b.closest("[data-group]")?.dataset.group);if(!g)return;
    if(b.dataset.removeGroup){
      const pizza=["sizes","flavors"].includes(g.type);
      if(!confirm(pizza?"Remover os blocos de tamanhos e sabores? Eles precisam ser usados juntos. Os pedidos já enviados serão preservados.":`Remover o bloco “${g.title}”? A alteração será aplicada ao salvar.`))return;
      for(let i=groups.length-1;i>=0;i--)if(pizza?["sizes","flavors"].includes(groups[i].type):groups[i]===g)groups.splice(i,1);
      render();return;
    }
    if(b.dataset.removeChoice){g.choices=g.choices.filter(c=>c.id!==b.dataset.removeChoice);opened.add(g.id);render();return;}
    if(b.dataset.addChoice || b.dataset.sizePreset!==undefined){
      if(g.choices.length>=(g.type==="flavors"?100:20)){show("Use até 100 sabores ou vinte opções nos outros blocos.",true);return;}
      let c;
      if(b.dataset.sizePreset!==undefined){
        const i=Number(b.dataset.sizePreset), names=["Broto","Média","Grande","Família"];
        const found=g.choices.find(c=>normalize(sizeParts(c).name)===normalize(names[i]));
        if(found){show("Esse tamanho já está cadastrado. Você pode ajustar a linha existente.");return;}
        c=choice(names[i]+" · "+[4,8,12,16][i]+" fatias",{max_flavors:[1,2,4,6][i]});
      } else c=choice("",g.type==="sizes"?{max_flavors:1}:{});
      g.choices.push(c);opened.add(g.id);render(g.id);
    }
  });
  function parseMoney(value, allowEmpty = false) {
    let raw = String(value ?? "").trim().replace(/^R\$\s*/i, "").trim();
    if (!raw && allowEmpty) return 0;
    let whole, fraction = "";
    if (/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?$/.test(raw)) {
      [whole, fraction = ""] = raw.replace(/\./g, "").split(",");
    } else if (/^\d+\.\d{1,2}$/.test(raw)) {
      [whole, fraction] = raw.split(".");
    } else {
      throw Error("Informe um valor como 5,50, 5.50 ou 1.234,56.");
    }
    const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
    if (!Number.isSafeInteger(cents) || cents < 0 || cents > 100000000)
      throw Error("O valor deve ficar entre R$ 0,00 e R$ 1.000.000,00.");
    return cents;
  }
  function choiceAmount(g, c) {
    try { return parseMoney(c.amount ?? moneyInput(c), g.type !== "flavors"); }
    catch (failure) {
      const block = container.querySelector(`[data-group="${g.id}"]`);
      if (block) {block.open = true; opened.add(g.id);}
      const field = block?.querySelector(`[data-choice="${c.id}"] [data-choice-field="amount"]`);
      field?.setAttribute("aria-invalid", "true");
      requestAnimationFrame(() => {field?.focus();field?.scrollIntoView({block:"center",behavior:"smooth"});});
      throw Error(`Bloco “${g.title}”, opção “${c.label || "sem nome"}”: ${failure.message}`);
    }
  }
  function validateEditor(){
    function invalid(g,text){opened.add(g.id);render();throw Error(text);}
    if(groups.length>(data.pizzaMenu ? 6 : 8))throw Error(data.pizzaMenu ? "Use até seis blocos de complementos." : "Use até oito blocos por produto.");
    const sizes=groups.filter(g=>g.enabled&&g.type==="sizes"), flavors=groups.filter(g=>g.enabled&&g.type==="flavors");
    if((sizes.length||flavors.length)&&(sizes.length!==1||flavors.length!==1))throw Error("A pizza precisa de um bloco de tamanhos e um de sabores ativos. Use os botões Tamanhos de pizza e Sabores da pizza para completar.");
    for(const g of groups){
      if(!g.title.trim()||g.title.trim().length>48)invalid(g,"Preencha o nome do bloco com até 48 caracteres.");
      if(g.type!=="text"&&g.enabled&&!g.choices.some(c=>c.enabled))invalid(g,`Adicione pelo menos uma opção visível em ${g.title}.`);
      if(g.type==="multiple"&&(!Number.isInteger(g.max)||g.max<1||g.max>20))invalid(g,`Defina um limite entre 1 e 20 em ${g.title}.`);
      for(const c of g.type==="text"?[]:g.choices){
        if(!c.label.trim()||c.label.trim().length>60)invalid(g,`Preencha o nome de cada opção de ${g.title}, com até 60 caracteres.`);
        if(g.type==="sizes"&&(!Number.isInteger(Number(c.max_flavors))||Number(c.max_flavors)<1||Number(c.max_flavors)>20))invalid(g,`Defina de 1 a 20 sabores para ${c.label}.`);
      }
    }
  }
  async function send(url, payload) {
    const response = await fetch(restaurantURL(url), {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')
          .content,
      },
      body: JSON.stringify(payload),
    });
    const raw = await response.text();
    let result;
    try {
      result = JSON.parse(raw);
      if (!result || typeof result !== "object" || Array.isArray(result))
        throw Error();
    } catch {
      const doc = new DOMParser().parseFromString(raw, "text/html");
      const panel = [...doc.querySelectorAll("section.panel")].find((element) =>
        element
          .querySelector("h1")
          ?.textContent.includes("Não foi possível concluir"),
      );
      const detail = (
        panel?.querySelector("p") || doc.querySelector("body > p")
      )?.textContent
        .trim()
        .slice(0, 600);
      const error = Error(
        detail
          ? `${detail} (HTTP ${response.status})`
          : `O servidor não devolveu uma mensagem de erro legível (HTTP ${response.status}). Encerre e reinicie o servidor antes de tentar novamente; suas alterações continuam nesta tela.`,
      );
      error.status = response.status;
      if (response.status === 403 && detail?.includes("Confirme a senha"))
        error.code = "management_auth_required";
      throw error;
    }
    if (!response.ok || !result.ok) {
      const error = Error(result.error || "Não foi possível salvar as opções.");
      error.status = response.status;
      error.code = result.code;
      throw error;
    }
    return result;
  }
  function confirmAccess() {
    return new Promise((resolve) => {
      const dialog = document.createElement("dialog");
      dialog.className = "app-dialog";
      dialog.setAttribute("aria-labelledby", "options-auth-title");
      dialog.innerHTML = `<form><div class="dialog-head"><h2 id="options-auth-title">Confirme sua senha</h2><button type="button" class="icon-button" aria-label="Cancelar">×</button></div><p>Esta área foi bloqueada. Suas opções continuam preenchidas.</p><label>Senha do administrador<input type="password" name="senha" autocomplete="current-password" required maxlength="256"></label><p role="status" class="error" hidden></p><button type="submit">Confirmar e salvar</button></form>`;
      const authForm = dialog.querySelector("form"),
        field = authForm.elements.senha,
        error = dialog.querySelector('[role="status"]');
      let confirmed = false;
      const finish = () => {
        field.value = "";
        dialog.remove();
        resolve(confirmed);
      };
      dialog.addEventListener("close", finish, { once: true });
      dialog.querySelector('[type="button"]').onclick = () => dialog.close();
      authForm.onsubmit = async (event) => {
        event.preventDefault();
        const button = authForm.querySelector('[type="submit"]');
        button.disabled = true;
        field.disabled = true;
        try {
          await send(form.dataset.unlockUrl, {
            destino: form.dataset.destination,
            senha: field.value,
          });
          confirmed = true;
          dialog.close();
        } catch (failure) {
          error.hidden = false;
          error.textContent = failure.message;
        } finally {
          button.disabled = false;
          field.disabled = false;
          if (dialog.open) field.focus();
        }
      };
      document.body.append(dialog);
      dialog.showModal();
      field.focus();
    });
  }
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (saving) return;
    let payload;
    try {
      validateEditor();
      payload = {
        version,
        notes: {
          enabled: document.querySelector("#notes-enabled").checked,
          label: document.querySelector("#notes-label").value.trim(),
          placeholder: document
            .querySelector("#notes-placeholder")
            .value.trim(),
        },
        groups: groups.map((g) => ({
          ...g,
          choices:
            g.type === "text"
              ? []
              : g.choices.map((c) => {
                  const cents = choiceAmount(g, c);
                  return {
                    id: c.id,
                    label: c.label,
                    description: c.description || "",
                    enabled: c.enabled,
                    max_flavors: Number(c.max_flavors || 1),
                    price: cents,
                  };
                }),
        })),
      };
      if (data.pizzaMenu) {
        const pricing_mode = document.querySelector("#pizza-pricing-mode").value;
        const sizes = [...document.querySelectorAll("[data-size-config]")].map(row => {
          const id=row.dataset.sizeConfig, enabled=row.querySelector("[data-size-enabled]").checked;
          const slices=Number(row.querySelector("[data-size-slices]").value), max_flavors=Number(row.querySelector("[data-size-limit]").value);
          if(!Number.isInteger(slices)||slices<1||slices>100||!Number.isInteger(max_flavors)||max_flavors<1||max_flavors>20)throw Error(`Confira as fatias e o limite de sabores de ${id}.`);
          let amount;
          try {amount=parseMoney(row.querySelector("[data-size-amount]").value,!enabled);}
          catch(error){row.querySelector("[data-size-amount]").focus();throw Error(`Preço de ${id}: ${error.message}`);}
          return {id,enabled,slices,max_flavors,amount};
        });
        payload={version,pricing_mode,sizes,modifiers:payload.groups,notes:payload.notes};
      }
    } catch (e) {
      show(e.message, true);
      return;
    }
    saving = true;
    form
      .querySelectorAll("input,select,textarea,button")
      .forEach((el) => (el.disabled = true));
    try {
      let response;
      try {
        response = await send(form.dataset.url, payload);
      } catch (failure) {
        if (
          failure.status !== 403 ||
          failure.code !== "management_auth_required"
        )
          throw failure;
        if (!(await confirmAccess())) {
          show(
            "Salvamento cancelado. Suas alterações continuam nesta tela.",
            true,
          );
          return;
        }
        response = await send(form.dataset.url, payload);
      }
      version = response.version;
      window.location.assign(
        form.dataset.destination || restaurantURL("/cadastros/produtos"),
      );
    } catch (e) {
      show(e.message, true);
    } finally {
      saving = false;
      form
        .querySelectorAll("input,select,textarea,button")
        .forEach((el) => (el.disabled = false));
    }
  });
  if (data.pizzaMenu) {
    document.querySelector("#pizza-category").onchange = event => window.location.assign(event.target.value);
    const mode=document.querySelector("#pizza-pricing-mode");
    function priceLabels(){
      const fixed=mode.value === "fixed";
      document.querySelectorAll("[data-size-price-label]").forEach(label=>label.textContent=fixed?"Preço da pizza (R$)":"Acréscimo ao preço dos sabores (R$)");
      document.querySelector("#pizza-price-help").textContent=fixed?"Cada tamanho tem seu preço. Os sabores estão incluídos; massa, borda e acompanhamentos somam os extras configurados.":"O valor é a média dos sabores escolhidos mais o acréscimo do tamanho. Use 0,00 para manter apenas a média.";
    }
    mode.onchange=()=>{document.querySelectorAll("[data-size-amount]").forEach(input=>input.value="");priceLabels();show("Você mudou a forma de cobrar. Defina os valores dos tamanhos antes de salvar.");};
    form.addEventListener("input",event=>{if(event.target.closest("[data-size-config]"))summary();});
    const importButton=document.querySelector("#pizza-import-legacy");
    if(importButton)importButton.onclick=async()=>{
      importButton.disabled=true;
      try{const result=await send(importButton.dataset.url,{});document.querySelector("#pizza-import-message").textContent=`${result.imported} sabores importados. Reabra esta configuração para atualizar a lista.`;importButton.hidden=true;}
      catch(error){document.querySelector("#pizza-import-message").textContent=error.message;importButton.disabled=false;}
    };
    priceLabels();
  }
  render();
})();
