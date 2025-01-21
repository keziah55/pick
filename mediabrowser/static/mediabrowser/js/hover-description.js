function hover_film(s) {

    // show film description on hover
    div = document.getElementById("description-hover");
    
    if (div !== null) 
        div.innerHTML = s;
}

function hover_film_grid(s, row_count) {
   // make grid of thumbnails from ;-separated string of url/uri
   // row_count is number of thumbnails per row

    var imgs = s.split(';');
    
    var html = '<div class="img-grid">';
    
    for (var i = 0; i < imgs.length; i++) {
        img_src = imgs[i];
        html += _make_img_item(img_src, i, row_count);
        }
    
    html += "</div></div>";
    
    hover_film(html);
       
}

function _make_img_item(img_src, index, row_count) {

    var html = ""

    if (index % row_count == 0) {
        if (index != 0) {
            html += "</div>"
        }
        html += '<div class="img-grid-row">'
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