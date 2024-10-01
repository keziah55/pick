function set_star_colour(element, filmId) {

    // get id number of clicked star
    var value = parseInt(element.id.slice(5, 6)); // star number is 5th char of id
    
    set_all_star_colours(element, filmId, value);
}
    
function set_all_star_colours(element, filmId, rating) {    

    style = window.getComputedStyle(element);
    colour = style.getPropertyValue("--foreground-2");
    noneColour = style.getPropertyValue("--none-colour");
    
    // set colour of all stars with IDs up to `value`
    var numStars = 5;
    
    for (var i=1; i<numStars+1; i++) {
        // get star button
        var starId = `star-${i}-${filmId}`;
        var element = document.getElementById(starId);
        
        // set colour
        if (i <= rating) {
           element.style.color = colour;
        } else {
            element.style.color = noneColour;
        }
    }  
}
