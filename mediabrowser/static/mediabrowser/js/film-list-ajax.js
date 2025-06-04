
$(document).on('submit', '#search-filter', function(e){ 
    e.preventDefault(); 
    
    var div_id = '#film-list';
    
    $.ajax({ 
        type: 'GET', 
        url: '/', 
        data: $("#search-filter").serialize(), 
        success: function(data){
            console.log("success, updating div ", div_id);
            $(div_id).html( data );
        },
        error: function(error){
            console.log("error setting film list: ", error);
        },
    }) 
}); 
