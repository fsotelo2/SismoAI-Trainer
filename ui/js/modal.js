(() => {
  "use strict";

  window.showConfirmDialog = function ({
    title = "Confirmar eliminación",
    subtitle = "Esta acción no se puede deshacer.",
    message = "¿Deseas continuar?",
    confirmLabel = "Eliminar",
  } = {}) {
    return new Promise((resolve) => {
      const modal = document.createElement("div");
      modal.className = "sismo-confirm-modal";
      modal.setAttribute("role", "presentation");
      modal.innerHTML =
        '<section class="sismo-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="sismo-confirm-title">' +
        '<header class="sismo-confirm-header"><div><h2 id="sismo-confirm-title"></h2><p class="sismo-confirm-subtitle"></p></div>' +
        '<button class="sismo-confirm-close" type="button" aria-label="Cerrar">×</button></header>' +
        '<div class="sismo-confirm-body"></div>' +
        '<footer class="sismo-confirm-footer"><button class="btn btn-secondary sismo-confirm-cancel" type="button">Cancelar</button>' +
        '<button class="btn btn-danger sismo-confirm-accept" type="button"></button></footer></section>';
      modal.querySelector("#sismo-confirm-title").textContent = title;
      modal.querySelector(".sismo-confirm-subtitle").textContent = subtitle;
      modal.querySelector(".sismo-confirm-body").textContent = message;
      modal.querySelector(".sismo-confirm-accept").textContent = confirmLabel;

      let settled = false;
      const close = (accepted) => {
        if (settled) return;
        settled = true;
        modal.classList.remove("is-open");
        window.setTimeout(() => modal.remove(), 160);
        document.removeEventListener("keydown", onKeyDown);
        resolve(accepted);
      };
      const onKeyDown = (event) => {
        if (event.key === "Escape") close(false);
      };
      modal.querySelector(".sismo-confirm-close").addEventListener("click", () => close(false));
      modal.querySelector(".sismo-confirm-cancel").addEventListener("click", () => close(false));
      modal.querySelector(".sismo-confirm-accept").addEventListener("click", () => close(true));
      modal.addEventListener("click", (event) => {
        if (event.target === modal) close(false);
      });
      document.addEventListener("keydown", onKeyDown);
      document.body.appendChild(modal);
      window.requestAnimationFrame(() => modal.classList.add("is-open"));
      modal.querySelector(".sismo-confirm-cancel").focus();
    });
  };
})();
