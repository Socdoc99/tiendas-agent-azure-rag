const form = document.querySelector("#chat-form");
const questionField = document.querySelector("#question");
const messages = document.querySelector("#messages");
const statusField = document.querySelector("#status");
const sendButton = document.querySelector("#send-button");
const sendLabel = document.querySelector("#send-label");
const history = [];

function addMessage(role, text, citations = []) {
  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;

  if (role !== "user") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "T";
    article.append(avatar);
  }

  const body = document.createElement("div");
  body.className = "message-body";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  body.append(paragraph);

  if (citations.length) {
    const sourceList = document.createElement("section");
    sourceList.className = "citations";
    const heading = document.createElement("h2");
    heading.textContent = "Fuentes";
    sourceList.append(heading);
    for (const citation of citations) {
      const item = document.createElement("div");
      item.className = "citation";
      const page = citation.page === null ? "sin pagina" : `pagina ${citation.page}`;
      item.textContent = `${citation.source_id} · ${citation.document_name} · ${page}`;
      sourceList.append(item);
    }
    body.append(sourceList);
  }

  article.append(body);
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = questionField.value.trim();
  if (!message) return;

  addMessage("user", message);
  history.push({ role: "user", content: message });
  questionField.value = "";
  statusField.textContent = "";
  sendButton.disabled = true;
  sendLabel.textContent = "Buscando...";

  try {
    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: history.slice(0, -1).slice(-8) }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error?.message || "No se pudo completar la consulta.");
    }
    addMessage("assistant", payload.answer, payload.citations || []);
    history.push({ role: "assistant", content: payload.answer });
    if (history.length > 8) history.splice(0, history.length - 8);
  } catch (error) {
    statusField.textContent = error.message || "Ocurrio un error al consultar los documentos.";
  } finally {
    sendButton.disabled = false;
    sendLabel.textContent = "Enviar";
    questionField.focus();
  }
});
