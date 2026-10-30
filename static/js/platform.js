"use strict";
document.querySelectorAll('[data-cpf]').forEach(input => {
  input.addEventListener('input', () => {
    const n=input.value.replace(/\D/g,'').slice(0,11);
    input.value=n.replace(/^(\d{3})(\d)/,'$1.$2').replace(/^(\d{3})\.(\d{3})(\d)/,'$1.$2.$3').replace(/(\d{3})\.(\d{3})\.(\d{3})(\d)/,'$1.$2.$3-$4');
  });
});
document.querySelectorAll('form').forEach(form => {
  if (!form.querySelector('[name="admin_nome"]')) return;
  const error=document.createElement('p'); error.className='error'; error.role='alert'; error.hidden=true; form.prepend(error);
  form.addEventListener('submit', async event => {
    event.preventDefault(); const button=form.querySelector('button[type="submit"],button:not([type])');
    error.hidden=true; if(button) button.disabled=true;
    try {
      const response=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{Accept:'application/json'}});
      if(response.redirected){ location.assign(response.url); return; }
      if(!response.ok){ const data=await response.json(); throw new Error(data.error || 'Não foi possível salvar. Confira os campos.'); }
      location.reload();
    } catch(err){error.textContent=err.message;error.hidden=false;error.scrollIntoView({block:'center'});}
    finally{if(button)button.disabled=false;}
  });
});

document.querySelectorAll('input[name="nascimento"]').forEach(input=>{const now=new Date();input.max=now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')+'-'+String(now.getDate()).padStart(2,'0');});
