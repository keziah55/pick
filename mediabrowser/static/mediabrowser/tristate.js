function tri_state_changed(element) {
    // set next state of tristate button `element`
    // cycle through states: 0:neutral, 1:include, 2:neutral, 3:exclude
    
    cStyle = window.getComputedStyle(element);
    colors = [cStyle.getPropertyValue("--neutral-color"),
              cStyle.getPropertyValue("--include-color"),
              cStyle.getPropertyValue("--neutral-color"),
              cStyle.getPropertyValue("--exclude-color")]
              
    var newState = parseInt(element.dataset.customState) + 1;
    if (newState >= 4)
        newState = 0;
    
    element.style.backgroundColor = colors[newState];
    element.style.color = colors[newState];
    element.dataset.customState = newState.toString();
    element.value = newState.toString();
    
    if (element.name == "all-genre-box")
        set_all_genres(element.dataset.customState, colors[newState]);
}

function set_all_genres(state, color) {
    // set state (and background colur) of all genre boxes
    checkboxes = document.getElementsByClassName('genrebox');
    for (var i=0, n=checkboxes.length;i<n;i++) {
        checkboxes[i].dataset.customState = state;
        checkboxes[i].style.backgroundColor = color;
        checkboxes[i].style.color = color;
        checkboxes[i].value = state;
    }
}