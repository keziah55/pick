
$(document).on('submit', '#star-rating', function(e){ 
    e.preventDefault(); 
    
    submitter = e.originalEvent.submitter.name;
    var fields = submitter.split('-');
    var film_pk = fields[2];
    var div_id = '#film-item-' + film_pk;
    
    console.log(submitter, film_pk);
    
    $.ajax({ 
        type: 'POST', 
        url: '/', 
        data: 
        { 
            submitter:submitter, 
            csrfmiddlewaretoken:$('input[name=csrfmiddlewaretoken]').val() 
        }, 
        success: function(data){
            console.log("success, updating div ", div_id);
            $(div_id).html( data );
        },
        error: function(error){
            console.log("error setting star rating for film_pk=", film_pk, ": ", error);
        },
    }) 
}); 
