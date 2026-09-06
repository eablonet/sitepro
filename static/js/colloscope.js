document.addEventListener('DOMContentLoaded', function () {

    // --- Bouton d'impression (page colloscope) ---
    var boutonImprimer = document.getElementById('bouton-imprimer');
    if (boutonImprimer) {
        boutonImprimer.addEventListener('click', function () {
            window.print();
        });
    }

    // --- Afficher / masquer le mot de passe (page d'accès) ---
    var bascule = document.getElementById('mdp-bascule');
    if (bascule) {
        var champ = document.getElementById(bascule.dataset.champ);
        bascule.addEventListener('click', function () {
            var visible = champ.type === 'text';
            champ.type = visible ? 'password' : 'text';
            bascule.setAttribute('aria-pressed', String(!visible));
            bascule.setAttribute(
                'aria-label',
                visible ? 'Afficher le mot de passe' : 'Masquer le mot de passe'
            );
            var icone = bascule.querySelector('i');
            icone.classList.toggle('ti-eye', visible);
            icone.classList.toggle('ti-eye-off', !visible);
        });
    }
});