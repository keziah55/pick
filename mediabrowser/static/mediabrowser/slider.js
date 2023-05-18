// https://stackoverflow.com/a/44384948

function rangeInputChangeEventHandler(e){
    var rangeGroup = $(this).attr('name'),
        minBtn = $(this).parent().children('.min'),
        maxBtn = $(this).parent().children('.max'),
        range_min = $(this).parent().children('.range_min'),
        range_max = $(this).parent().children('.range_max'),
        minVal = parseInt($(minBtn).val()),
        maxVal = parseInt($(maxBtn).val()),
        //origin = $(this).context.className;
        origin = e.originalEvent.target.className;

    if(origin === 'min' && minVal > maxVal-5){
        $(minBtn).val(maxVal-5);
    }
    var minVal = parseInt($(minBtn).val());
    $(range_min).html(minVal);


    if(origin === 'max' && maxVal-5 < minVal){
        $(maxBtn).val(5+ minVal);
    }
    var maxVal = parseInt($(maxBtn).val());
    $(range_max).html(maxVal);
    
    console.log(minVal);
    console.log(maxVal);
}

$('input[type="range"]').on( 'input', rangeInputChangeEventHandler);