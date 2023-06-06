function hover_film(s) {
    // show film description on hober
    p = document.getElementById("description-hover");
    p.innerHTML = s;
}

function hover_film_leave() {
    // hide film description on hover leave
    p = document.getElementById("description-hover");
    p.innerHTML = "";
}