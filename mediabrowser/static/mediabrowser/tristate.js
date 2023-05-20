function tri_state_changed(element) {
    
    // cycle through states: 0:neutral, 1:include, 2:neutral, 3:exclude
    
    cStyle = window.getComputedStyle(element);
    colors = [cStyle.getPropertyValue("--neutral-color"),
              cStyle.getPropertyValue("--include-color"),
              cStyle.getPropertyValue("--neutral-color"),
              cStyle.getPropertyValue("--exclude-color")]
              
    var currentState = parseInt(element.dataset.customState);
    var newState = currentState + 1;
    if (newState >= 4) {
        newState = 0;
    }
    
    element.style.backgroundColor = colors[newState];
    element.dataset.customState = newState.toString();
    
    if (element.name == "all-genre-box") {
        set_all_genres(element.dataset.customState, colors[newState]);
    }
}

function set_all_genres(state, color) {
    console.log("set_all_genres");
    checkboxes = document.getElementsByClassName('genrebox');
    for(var i=0, n=checkboxes.length;i<n;i++) {
        checkboxes[i].dataset.customState = state;
        checkboxes[i].style.backgroundColor = color;
    }
}