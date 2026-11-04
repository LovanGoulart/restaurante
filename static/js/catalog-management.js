"use strict";
document.querySelectorAll(".catalog-delete-form").forEach((form) =>
  form.addEventListener("submit", (event) => {
    if (
      !confirm(
        `Excluir "${form.dataset.deleteName}" do cadastro? O histórico dos pedidos será preservado.`,
      )
    )
      event.preventDefault();
  }),
);

(() => {
  const input = document.querySelector("#catalog-image");
  if (!input) return;
  const preview=document.querySelector("#catalog-image-preview"), placeholder=document.querySelector("#catalog-image-placeholder"), filename=document.querySelector("#catalog-image-filename"), remove=document.querySelector("#catalog-image-remove");
  let objectURL;
  function draw() {
    if(objectURL) {URL.revokeObjectURL(objectURL);objectURL=undefined;}
    const file=input.files[0];
    if(file&&file.size>5*1024*1024){input.value="";alert("A imagem deve ter no máximo 5 MB.");draw();return;}
    if(file){objectURL=URL.createObjectURL(file);preview.src=objectURL;preview.hidden=false;placeholder.hidden=true;filename.textContent=file.name;if(remove)remove.checked=false;}
    else if(remove?.checked){preview.hidden=true;placeholder.hidden=false;placeholder.textContent="A imagem será removida ao salvar.";filename.textContent="Remoção selecionada";}
    else {preview.hidden=!preview.dataset.current;if(preview.dataset.current)preview.src=preview.dataset.current;placeholder.hidden=!!preview.dataset.current;placeholder.textContent="Escolha uma foto para mostrar no cardápio.";filename.textContent=preview.dataset.current?"Imagem atual cadastrada":"Nenhuma imagem selecionada";}
  }
  input.addEventListener("change",draw);
  remove?.addEventListener("change",()=>{if(remove.checked)input.value="";draw();});
})();
