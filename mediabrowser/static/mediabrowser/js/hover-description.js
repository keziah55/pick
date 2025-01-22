function hover_film(s) {

    // show film description on hover
    div = document.getElementById("description-hover");
    
    if (div !== null) 
        div.innerHTML = s;
}

function hover_film_grid(s, row_len, max_rows) {
   // make grid of thumbnails from ;-separated string of url/uri
   // row_len is number of thumbnails per row
   
   let max_imgs = row_len * max_rows;

    let imgs = s.split(';');
    
    var html = '<div class="img-grid">';
    
    let iter_size = imgs.length < max_imgs ? imgs.length : max_imgs;
    
    console.log(iter_size, imgs.length, max_imgs);
    
    for (var i = 0; i < iter_size; i++) {
        img_src = imgs[i];
        html += _make_img_item(img_src, i, row_len);
        }
    
    html += "</div></div>";
    
    hover_film(html);
       
}

function _make_img_item(img_src, index, row_len) {

    var html = ""

    if (index % row_len == 0) {
        if (index != 0) {
            html += "</div>"
        }
        html += '<div class="img-grid-row">'
        }
    html += '<img class="film-thumbnail-small" src="' + img_src + '">'
    
    return html   
}

function hover_film_leave() {
    // hide film description on hover leave
    p = document.getElementById("description-hover");
    
    if (div !== null) 
        div.innerHTML = "";
}