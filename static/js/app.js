const modalConfirmacao = document.querySelector("[data-modal-confirmacao]");
const mensagemConfirmacao = document.querySelector("[data-mensagem-confirmacao]");
const botoesCancelarConfirmacao = document.querySelectorAll("[data-cancelar-confirmacao]");
const botaoConfirmarConfirmacao = document.querySelector("[data-confirmar-confirmacao]");

let formularioPendente = null;
let botaoPendente = null;

function obterMensagemConfirmacao(botao) {
  const texto = botao.textContent.trim().toLowerCase();
  const mensagemPersonalizada = botao.dataset.confirmacao;

  if (mensagemPersonalizada) {
    return mensagemPersonalizada;
  }

  if (texto.includes("sortear")) {
    return "Sortear as chaves e iniciar o torneio? Essa acao reinicia as partidas deste torneio.";
  }

  if (texto.includes("excluir")) {
    return "Excluir este registro? Essa acao nao pode ser desfeita.";
  }

  return "Remover este participante?";
}

function precisaConfirmar(botao) {
  const texto = botao.textContent.trim().toLowerCase();
  return Boolean(
    botao.dataset.confirmacao ||
      texto.includes("remover") ||
      texto.includes("sortear") ||
      texto.includes("excluir") ||
      texto.includes("desfazer")
  );
}

function abrirConfirmacao(formulario, botao) {
  if (!modalConfirmacao || !mensagemConfirmacao || !botaoConfirmarConfirmacao) {
    anexarValorBotao(formulario, botao);
    HTMLFormElement.prototype.submit.call(formulario);
    return;
  }

  formularioPendente = formulario;
  botaoPendente = botao;
  mensagemConfirmacao.textContent = obterMensagemConfirmacao(botao);
  modalConfirmacao.classList.add("ativo");
  modalConfirmacao.setAttribute("aria-hidden", "false");
  botaoConfirmarConfirmacao.focus();
}

function fecharConfirmacao() {
  if (!modalConfirmacao) {
    return;
  }

  modalConfirmacao.classList.remove("ativo");
  modalConfirmacao.setAttribute("aria-hidden", "true");
  formularioPendente = null;
  botaoPendente = null;
}

function anexarValorBotao(formulario, botao) {
  if (!botao.name || !botao.value) {
    return;
  }

  const campoExistente = Array.from(formulario.querySelectorAll("input[data-valor-botao]")).find(
    (campo) => campo.name === botao.name
  );
  if (campoExistente) {
    campoExistente.value = botao.value;
    return;
  }

  const campoOculto = document.createElement("input");
  campoOculto.type = "hidden";
  campoOculto.name = botao.name;
  campoOculto.value = botao.value;
  campoOculto.dataset.valorBotao = "true";
  formulario.appendChild(campoOculto);
}

function enviarFormularioConfirmado() {
  if (!formularioPendente || !botaoPendente) {
    return;
  }

  const formulario = formularioPendente;
  const botao = botaoPendente;
  anexarValorBotao(formulario, botao);
  fecharConfirmacao();
  formulario.classList.add("enviando");
  botao.disabled = true;
  HTMLFormElement.prototype.submit.call(formulario);
}

document.addEventListener("submit", (evento) => {
  const formulario = evento.target;
  const botaoClicado = evento.submitter;

  if (!botaoClicado) {
    return;
  }

  if (precisaConfirmar(botaoClicado)) {
    evento.preventDefault();
    abrirConfirmacao(formulario, botaoClicado);
    return;
  }

  anexarValorBotao(formulario, botaoClicado);
  formulario.classList.add("enviando");
  botaoClicado.disabled = true;
});

document.addEventListener("DOMContentLoaded", () => {
  const campoFocoCadastro = document.querySelector("[data-foco-cadastro]");

  if (campoFocoCadastro && !campoFocoCadastro.disabled) {
    campoFocoCadastro.focus();
  }
});

botoesCancelarConfirmacao.forEach((botao) => {
  botao.addEventListener("click", fecharConfirmacao);
});

if (botaoConfirmarConfirmacao) {
  botaoConfirmarConfirmacao.addEventListener("click", enviarFormularioConfirmado);
}

document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && modalConfirmacao && modalConfirmacao.classList.contains("ativo")) {
    fecharConfirmacao();
  }
});
