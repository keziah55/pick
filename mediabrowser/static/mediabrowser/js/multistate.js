function tri_state_changed(element) {
    // set next state of multistate button `element`
    // cycle through states: 0:neutral, 1:include, 2:neutral, 3:exclude
    
    style = window.getComputedStyle(element);
    colors = [style.getPropertyValue("--neutral-color"),
              style.getPropertyValue("--include-color"),
              style.getPropertyValue("--exclude-color")]
              
    var dataElement = document.getElementById(element.id + "-data");
    var newState = parseInt(dataElement.value) + 1;
    if (newState >= colors.length)
        newState = 0;
        
    set_multistate_state(element, newState.toString(), colors[newState]);
    
    if (element.name == "all-genre-box")
        set_all_genres(dataElement.value, colors[newState]);
}

function set_all_genres(state, color) {
    // set state (and background colour) of all genre boxes
    checkboxes = document.getElementsByClassName('genrebox');
    for (var i=0, n=checkboxes.length;i<n;i++) {
        set_multistate_state(checkboxes[i], state, color)
    }
}

function set_multistate_state(element, state, color) {
    // set `element` background colour and corresponding hidden data element `state`
    var dataElement = document.getElementById(element.id + "-data");
    element.style.backgroundColor = color;
    dataElement.value = state;
}