// https://stackoverflow.com/a/44384948

function rangeInputChangeEventHandler(e){
    var rangeGroup = $(this).attr('name'),
        minBtn = $(this).parent().children('.min'),
        maxBtn = $(this).parent().children('.max'),
        slider_range = $(this).parent().children('.slider_range'),
        minVal = parseInt($(minBtn).val()),
        maxVal = parseInt($(maxBtn).val()),
        //origin = $(this).context.className;
        origin = e.originalEvent.target.className;

    if(origin === 'min' && minVal > maxVal-5){
        $(minBtn).val(maxVal-5);
    }
    var minVal = parseInt($(minBtn).val());

    if(origin === 'max' && maxVal-5 < minVal){
        $(maxBtn).val(5+ minVal);
    }
    var maxVal = parseInt($(maxBtn).val());
    
    //console.log(minVal);
    //console.log(maxVal);
    
    $(slider_range).html(minVal + ' - ' + maxVal)
}

$('input[type="range"]').on( 'input', rangeInputChangeEventHandler);