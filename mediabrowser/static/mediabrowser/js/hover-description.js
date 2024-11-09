function hover_film(s) {
    // show film description on hover
    div = document.getElementById("description-hover");
    
    if (div !== null) 
        div.innerHTML = s;
}

function hover_film_leave() {
    // hide film description on hover leave
    div = document.getElementById("description-hover");
    
    if (div !== null) 
        div.innerHTML = "";
}