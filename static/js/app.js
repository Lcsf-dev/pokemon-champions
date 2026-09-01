document.addEventListener("submit", (evento) => {
  const formulario = evento.target;
  const botaoClicado = evento.submitter;

  if (!botaoClicado) {
    return;
  }

  const texto = botaoClicado.textContent.trim().toLowerCase();
  const mensagemPersonalizada = botaoClicado.dataset.confirmacao;
  const precisaConfirmar = mensagemPersonalizada || texto.includes("remover") || texto.includes("sortear") || texto.includes("excluir");

  if (precisaConfirmar) {
    let mensagem = mensagemPersonalizada;

    if (!mensagem) {
      mensagem = texto.includes("sortear")
        ? "Sortear as chaves e iniciar o torneio? Essa ação reinicia as partidas deste torneio."
        : "Remover este participante?";
    }

    if (!window.confirm(mensagem)) {
      evento.preventDefault();
      return;
    }
  }

  if (botaoClicado.name && botaoClicado.value) {
    const campoOculto = document.createElement("input");
    campoOculto.type = "hidden";
    campoOculto.name = botaoClicado.name;
    campoOculto.value = botaoClicado.value;
    formulario.appendChild(campoOculto);
  }

  formulario.classList.add("enviando");
  botaoClicado.disabled = true;
});