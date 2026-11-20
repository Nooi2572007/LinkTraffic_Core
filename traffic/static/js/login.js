(function () {
  "use strict";

  // イベント56：パスワード表示／非表示の切り替え
  var passwordInput = document.getElementById("id_password");
  var toggleButton = document.getElementById("password-toggle");
  if (passwordInput && toggleButton) {
    var icon = toggleButton.querySelector(".material-symbols-outlined");
    toggleButton.addEventListener("click", function () {
      var show = passwordInput.type === "password";
      passwordInput.type = show ? "text" : "password";
      toggleButton.setAttribute("aria-pressed", String(show));
      toggleButton.setAttribute("aria-label", show ? "パスワードを隠す" : "パスワードを表示");
      icon.textContent = show ? "visibility_off" : "visibility";
    });
  }

  // ロックポップアップ：ロック時に自動表示し、閉じるボタンで閉じる
  var popup = document.getElementById("lock-popup");
  var closeButton = document.getElementById("lock-popup-close");
  if (popup) {
    if (popup.dataset.openOnLoad === "true" && typeof popup.showModal === "function") {
      popup.showModal();
    }
    if (closeButton) {
      closeButton.addEventListener("click", function () { popup.close(); });
    }
  }
})();
