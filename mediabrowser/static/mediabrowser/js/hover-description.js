function hover_film(s) {

    // show film description on hover
    div = document.getElementById("description-hover");
    
        
    
    if (div !== null) 
        div.innerHTML = s;
}

function hover_film_grid(s) {

    var imgs = s.split(';');
    var column_count = 3;
    
    var html = '<div class="img-grid-row">';
    
    for (var i = 0; i < imgs.length; i++) {
        img_src = imgs[i];
        html += _make_img_item(img_src, i);
        }
    
    html += "</div></div>";
    
    console.log(html);
    
    hover_film(html);
    
    
}

function _make_img_item(img_src, index) {

    var html = ""

    if (index % 3 == 0) {
        if (index != 0) {
            html += "</div>"
        }
        html += '<div class="img-grid-column">'
        }
    html += '<img class="film-thumbnail-small" src="' + img_src + '">'
    
    console.log(html);
    
    return html   
}

function hover_film_leave() {
    // hide film description on hover leave
    p = document.getElementById("description-hover");
    
    if (div !== null) 
        div.innerHTML = "";
}