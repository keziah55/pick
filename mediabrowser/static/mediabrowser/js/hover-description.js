function hover_film(s) {

    // show film description on hover
    p = document.getElementById("description-hover");
    
    if (p !== null) 
        p.innerHTML = s;
}

function hover_film_leave() {
    // hide film description on hover leave
    p = document.getElementById("description-hover");
    
    if (p !== null) 
        p.innerHTML = "";
}