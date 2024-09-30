
$(document).on('submit','#star-rating',function(e){ 
    e.preventDefault(); 
    console.log(e.originalEvent.submitter.name);
    $.ajax({ 
        type:'POST', 
        url:'/', 
        data: 
        { 
            submitter:e.originalEvent.submitter.name, 
            csrfmiddlewaretoken:$('input[name=csrfmiddlewaretoken]').val() 
        }, 
        success:function(){ 
          } 
    }) 
}); 
