/* Caixa de saída offline do RDC Inteligente.
 *
 * Formulários marcados com data-offline="Rótulo" que forem enviados sem sinal (ou com o
 * servidor fora do ar) ficam guardados no aparelho (IndexedDB, inclusive as fotos) e são
 * reenviados sozinhos quando a conexão volta. Um selo no canto mostra quantos envios aguardam.
 *
 * Regra de entrega: o Django responde com redirecionamento quando grava. Resposta 200 sem
 * redirecionamento significa que o formulário voltou com erro: o item fica marcado para revisão.
 */
(function () {
  "use strict";
  var DB_NOME = "rdc-offline", DB_VERSAO = 1, LOJA = "envios";
  var TIMEOUT_MS = 12000;
  var enviando = false;

  function abrirBanco() {
    return new Promise(function (ok, erro) {
      if (!("indexedDB" in window)) { erro(new Error("sem IndexedDB")); return; }
      var req = indexedDB.open(DB_NOME, DB_VERSAO);
      req.onupgradeneeded = function () {
        var db = req.result;
        if (!db.objectStoreNames.contains(LOJA)) db.createObjectStore(LOJA, { keyPath: "id", autoIncrement: true });
      };
      req.onsuccess = function () { ok(req.result); };
      req.onerror = function () { erro(req.error); };
    });
  }

  function operar(modo, fn) {
    return abrirBanco().then(function (db) {
      return new Promise(function (ok, erro) {
        var tx = db.transaction(LOJA, modo);
        var resultado = fn(tx.objectStore(LOJA));
        tx.oncomplete = function () { ok(resultado && resultado.result !== undefined ? resultado.result : resultado); };
        tx.onerror = function () { erro(tx.error); };
      });
    });
  }

  function listar() { return operar("readonly", function (s) { return s.getAll(); }); }
  function guardar(item) { return operar("readwrite", function (s) { return s.put(item); }); }
  function remover(id) { return operar("readwrite", function (s) { return s.delete(id); }); }

  function cookie(nome) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + nome + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  function serializar(form) {
    var campos = [];
    new FormData(form).forEach(function (valor, nome) {
      if (valor instanceof File) {
        if (valor.size) campos.push({ nome: nome, arquivo: valor, arquivoNome: valor.name, tipo: valor.type });
      } else {
        campos.push({ nome: nome, valor: valor });
      }
    });
    return campos;
  }

  function montarCorpo(campos) {
    var fd = new FormData();
    campos.forEach(function (c) {
      if (c.nome === "csrfmiddlewaretoken") return;  // troca pelo token atual
      if (c.arquivo) fd.append(c.nome, c.arquivo, c.arquivoNome || "foto.jpg");
      else fd.append(c.nome, c.valor);
    });
    fd.append("csrfmiddlewaretoken", cookie("csrftoken"));
    return fd;
  }

  function comTempo(promessa, ms) {
    return new Promise(function (ok, erro) {
      var t = setTimeout(function () { erro(new Error("tempo esgotado")); }, ms);
      promessa.then(function (r) { clearTimeout(t); ok(r); }, function (e) { clearTimeout(t); erro(e); });
    });
  }

  function enviar(item) {
    return comTempo(fetch(item.url, {
      method: "POST", body: montarCorpo(item.campos), credentials: "same-origin",
      headers: { "X-CSRFToken": cookie("csrftoken"), "X-Envio-Offline": "1" }, redirect: "follow",
    }), TIMEOUT_MS);
  }

  /* ---------- selo e painel ---------- */
  function garantirSelo() {
    var selo = document.getElementById("rdc-offline-selo");
    if (selo) return selo;
    var estilo = document.createElement("style");
    estilo.textContent =
      "#rdc-offline-selo{position:fixed;right:14px;bottom:14px;z-index:1080;display:none;border:0;border-radius:999px;" +
      "padding:.55rem .9rem;font:700 .85rem var(--dg-font,system-ui);background:#12171c;color:#fff;box-shadow:0 10px 26px rgba(0,0,0,.25)}" +
      "#rdc-offline-selo .p{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:#f59e0b;margin-right:.45rem}" +
      "#rdc-offline-selo.erro .p{background:#ef4444}#rdc-offline-selo.sem-sinal .p{background:#9ca3af}" +
      "#rdc-offline-painel{position:fixed;right:14px;bottom:64px;z-index:1080;width:min(360px,calc(100vw - 28px));max-height:60vh;overflow:auto;" +
      "background:#fff;border:1px solid #e6e3dd;border-radius:14px;box-shadow:0 18px 40px rgba(0,0,0,.2);padding:.9rem;display:none;font-size:.88rem}" +
      "#rdc-offline-painel li{list-style:none;border-bottom:1px solid #eee;padding:.45rem 0}#rdc-offline-painel ul{padding:0;margin:.5rem 0}" +
      "#rdc-offline-aviso{position:fixed;left:50%;transform:translateX(-50%);top:14px;z-index:1090;background:#12171c;color:#fff;" +
      "padding:.7rem 1rem;border-radius:12px;box-shadow:0 12px 30px rgba(0,0,0,.3);font-weight:600;max-width:92vw;display:none}";
    document.head.appendChild(estilo);
    selo = document.createElement("button");
    selo.id = "rdc-offline-selo"; selo.type = "button";
    selo.addEventListener("click", alternarPainel);
    document.body.appendChild(selo);
    var painel = document.createElement("div");
    painel.id = "rdc-offline-painel";
    document.body.appendChild(painel);
    var aviso = document.createElement("div");
    aviso.id = "rdc-offline-aviso"; aviso.setAttribute("role", "status");
    document.body.appendChild(aviso);
    return selo;
  }

  function avisar(texto) {
    garantirSelo();
    var a = document.getElementById("rdc-offline-aviso");
    a.textContent = texto; a.style.display = "block";
    clearTimeout(avisar._t);
    avisar._t = setTimeout(function () { a.style.display = "none"; }, 4500);
  }

  function atualizarSelo() {
    return listar().then(function (itens) {
      var selo = garantirSelo();
      var erros = itens.filter(function (i) { return i.revisar; }).length;
      if (!itens.length) { selo.style.display = "none"; document.getElementById("rdc-offline-painel").style.display = "none"; return itens; }
      selo.className = erros ? "erro" : (navigator.onLine ? "" : "sem-sinal");
      selo.innerHTML = '<span class="p"></span>' + itens.length + " envio(s) aguardando" + (navigator.onLine ? "" : " · sem sinal");
      selo.style.display = "block";
      if (document.getElementById("rdc-offline-painel").style.display === "block") desenharPainel(itens);
      document.dispatchEvent(new CustomEvent("rdc-offline-fila", { detail: { total: itens.length, erros: erros } }));
      return itens;
    }).catch(function () { return []; });
  }

  function desenharPainel(itens) {
    var painel = document.getElementById("rdc-offline-painel");
    var html = "<strong>Caixa de saída</strong><div style='color:#5b6670'>Guardado neste aparelho. Envia sozinho quando houver sinal.</div><ul>";
    itens.forEach(function (i) {
      var fotos = i.campos.filter(function (c) { return c.arquivo; }).length;
      html += "<li><div><b>" + escapar(i.rotulo) + "</b>" + (fotos ? " · " + fotos + " foto(s)" : "") + "</div>" +
        "<div style='color:#5b6670'>" + new Date(i.criadoEm).toLocaleString("pt-BR") + (i.tentativas ? " · " + i.tentativas + " tentativa(s)" : "") + "</div>" +
        (i.revisar ? "<div style='color:#b42318'>" + escapar(i.revisar) + " <a href='" + i.pagina + "'>abrir formulário</a></div>" : "") +
        "<button type='button' data-descartar='" + i.id + "' style='border:0;background:none;color:#b42318;padding:0;font-size:.8rem'>descartar</button></li>";
    });
    html += "</ul><button type='button' id='rdc-offline-enviar' class='btn btn-sm btn-primary w-100'>Enviar agora</button>";
    painel.innerHTML = html;
    painel.querySelectorAll("[data-descartar]").forEach(function (b) {
      b.addEventListener("click", function () {
        if (confirm("Descartar este envio? Ele não foi para o servidor.")) remover(Number(b.getAttribute("data-descartar"))).then(atualizarSelo);
      });
    });
    document.getElementById("rdc-offline-enviar").addEventListener("click", function () { esvaziar(true); });
  }

  function alternarPainel() {
    var painel = document.getElementById("rdc-offline-painel");
    if (painel.style.display === "block") { painel.style.display = "none"; return; }
    listar().then(function (itens) { desenharPainel(itens); painel.style.display = "block"; });
  }

  function escapar(t) { var d = document.createElement("div"); d.textContent = String(t || ""); return d.innerHTML; }

  /* ---------- envio da fila ---------- */
  function esvaziar(manual) {
    if (enviando) return Promise.resolve();
    if (!navigator.onLine && !manual) return atualizarSelo();
    enviando = true;
    var entregues = 0;
    return listar().then(function (itens) {
      return itens.filter(function (i) { return !i.revisar || manual; }).reduce(function (cadeia, item) {
        return cadeia.then(function () {
          return enviar(item).then(function (resp) {
            if (resp.ok && resp.redirected) { entregues++; return remover(item.id); }
            item.tentativas = (item.tentativas || 0) + 1;
            item.revisar = resp.status === 403 ? "Sessão expirada: entre de novo no sistema." :
              resp.ok ? "O servidor recusou os dados (confira o formulário)." : "Erro " + resp.status + " no servidor.";
            return guardar(item);
          }, function () {
            item.tentativas = (item.tentativas || 0) + 1;
            return guardar(item).then(function () { throw new Error("sem conexão"); });
          });
        });
      }, Promise.resolve());
    }).catch(function () { /* sem conexão: tenta de novo depois */ })
      .then(function () {
        enviando = false;
        if (entregues) avisar(entregues + " envio(s) guardado(s) foram entregues ao servidor.");
        return atualizarSelo();
      });
  }

  /* ---------- captura dos formulários ---------- */
  function guardarFormulario(form) {
    var item = {
      url: form.getAttribute("action") ? new URL(form.getAttribute("action"), location.href).href : location.href,
      pagina: location.href, rotulo: form.getAttribute("data-offline") || document.title,
      campos: serializar(form), criadoEm: Date.now(), tentativas: 0,
    };
    var submissor = form._rdcSubmissor;
    if (submissor && submissor.name) item.campos.push({ nome: submissor.name, valor: submissor.value });
    return guardar(item).then(function () {
      avisar("Sem sinal: \"" + item.rotulo + "\" ficou guardado no aparelho e será enviado quando a conexão voltar.");
      form.reset();
      atualizarSelo();
      setTimeout(function () { if (history.length > 1) history.back(); }, 1800);
    });
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest("button[type=submit],input[type=submit]");
    if (b && b.form) b.form._rdcSubmissor = b;
  }, true);

  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (!form.matches || !form.matches("form[data-offline]") || form._rdcEnviandoOnline) return;
    ev.preventDefault();
    var reabilitar = function () { form.querySelectorAll("[type=submit]").forEach(function (b) { b.disabled = false; }); };
    if (!navigator.onLine) { guardarFormulario(form).then(reabilitar); return; }
    // Com sinal: testa o servidor rápido; se não responder, guarda.
    comTempo(fetch("/offline/", { method: "HEAD", cache: "no-store", credentials: "same-origin" }), 5000)
      .then(function () { form._rdcEnviandoOnline = true; HTMLFormElement.prototype.submit.call(form); })
      .catch(function () { guardarFormulario(form).then(reabilitar); });
  }, true);

  /* ---------- deixa as telas de campo prontas para abrir sem sinal ---------- */
  function aquecerCache() {
    if (!navigator.onLine || !("serviceWorker" in navigator)) return;
    var ultimo = Number(localStorage.getItem("rdc-offline-aquecido") || 0);
    if (Date.now() - ultimo < 60 * 60 * 1000) return;
    fetch("/m/offline-urls/", { credentials: "same-origin" }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (dados) {
        if (!dados) return;
        localStorage.setItem("rdc-offline-aquecido", String(Date.now()));
        dados.urls.reduce(function (cadeia, url) {
          return cadeia.then(function () { return fetch(url, { credentials: "same-origin" }).catch(function () {}); });
        }, Promise.resolve());
      }).catch(function () {});
  }

  window.RDCOffline = { listar: listar, esvaziar: esvaziar, atualizar: atualizarSelo, aquecer: aquecerCache };
  window.addEventListener("online", function () { esvaziar(false); });
  window.addEventListener("offline", atualizarSelo);
  document.addEventListener("DOMContentLoaded", function () {
    atualizarSelo().then(function () { esvaziar(false); });
    setTimeout(aquecerCache, 3000);
  });
  setInterval(function () { esvaziar(false); }, 60000);
})();
