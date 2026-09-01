document.addEventListener("submit", (evento) => {
  const formulario = evento.target;
  const botaoClicado = evento.submitter;

  if (!botaoClicado) {
    return;
  }

  const texto = botaoClicado.textContent.trim().toLowerCase();
  const precisaConfirmar = texto.includes("remover") || texto.includes("sortear");

  if (!precisaConfirmar) {
    return;
  }

  const mensagem = texto.includes("sortear")
    ? "Sortear as chaves e iniciar o torneio? Essa ação reinicia as partidas deste torneio."
    : "Remover este participante?";

  if (!window.confirm(mensagem)) {
    evento.preventDefault();
    return;
  }

  formulario.classList.add("enviando");
  botaoClicado.disabled = true;
});
