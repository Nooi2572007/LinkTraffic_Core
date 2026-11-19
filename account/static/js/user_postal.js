document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('btn-search-address');
    const postCodeInput = document.getElementById('id_post_code');
    const addressInput = document.getElementById('id_address');

    if (!searchBtn || !postCodeInput || !addressInput) {
        return;
    }

    searchBtn.addEventListener('click', async () => {
        const zipcode = postCodeInput.value.replace(/[^0-9]/g, '');
        if (zipcode.length !== 7) {
            alert('郵便番号は7桁の数字で入力してください。');
            return;
        }

        try {
            const response = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${zipcode}`);
            const data = await response.json();

            if (data.results && data.results.length > 0) {
                const result = data.results[0];
                addressInput.value = `${result.address1}${result.address2}${result.address3}`;
            } else {
                alert('該当する住所が見つかりませんでした。');
            }
        } catch (error) {
            alert('住所検索に失敗しました。時間をおいて再度お試しください。');
        }
    });
});