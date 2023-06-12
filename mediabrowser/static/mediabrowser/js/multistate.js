function tri_state_changed(element) {
    // set next state of multistate button `element`
    // cycle through states: 0:neutral, 1:AND, 2:OR, 3:NOT
    values = ['\u2015', "AND", "OR", "NOT"];
              
    var dataElement = document.getElementById(element.id + "-data");
    var newState = parseInt(dataElement.value) + 1;
    if (newState >= values.length)
        newState = 0;
        
    set_multistate_state(element, newState.toString(), values[newState]);
    
    if (element.name == "all-genre-box")
        set_all_genres(dataElement.value, values[newState]);
}

function set_all_genres(state, value) {
    // set state (and background colour) of all genre boxes
    checkboxes = document.getElementsByClassName('genrebox');
    for (var i=0, n=checkboxes.length;i<n;i++) {
        set_multistate_state(checkboxes[i], state, value)
    }
}

function set_multistate_state(element, state, value) {
    // set `element` background colour and corresponding hidden data element `state`
    var dataElement = document.getElementById(element.id + "-data");
    element.value = value;
    dataElement.value = state;
}