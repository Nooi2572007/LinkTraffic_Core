function togglePassword() {
    const pw = document.getElementById("id_password");
    const chk = document.getElementById("show_pass");
    pw.type = chk.checked ? "text" : "password";
}

document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = document.getElementById('menuListBtn');
    const menuList = document.getElementById('menuList');

    if (menuBtn && menuList) {
        menuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            menuList.classList.toggle('is-open');
        });
        document.addEventListener('click', (e) => {
            if (!menuList.contains(e.target) && !menuBtn.contains(e.target)) {
                menuList.classList.remove('is-open');
            }
        });
    }
});