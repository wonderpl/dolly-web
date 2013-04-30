function PreviewImage() {
    oFReader = new FileReader();
    oFReader.readAsDataURL($("#cover").prop("files")[0]);

    oFReader.onload = function (oFREvent) {
        ShowImage(oFREvent.target.result)
    };
}

function ShowImage(imgSrc) {
    $("#uploadPreview").attr({'src': imgSrc});
    $("#uploadPreview").load(function() {
        PositionSelector();
    })
}

function PositionSelector() {
    var containerSize = [$("#container").width(), $("#container").height()],
        selectoraoi = $("#cover_aoi").val().substring(1,$("#cover_aoi").val().length -1).split(","),
        originalBoxSize = [202,300], // Original size for inner Box
        originalSelectorSize = [400, 357], // Original selector for inner Box
        Ratio = ((selectoraoi[3] - selectoraoi[1])*containerSize[1]) / originalBoxSize[1],
        currentSize = [Math.round(originalSelectorSize[0]* Ratio), Math.round(originalSelectorSize[1] * Ratio)];

    selectoraoi[0] = Math.round(selectoraoi[0]*containerSize[0] - (currentSize[0]*0.26));
    selectoraoi[1] = Math.round(selectoraoi[1]*containerSize[1] - (currentSize[1]*0.08));
    $("#selector").css({'left': selectoraoi[0], 'top' : selectoraoi[1], width: currentSize[0], height: currentSize[1]});
    $("#selector").show().draggable({ containment: "parent" }).resizable({
        aspectRatio: 400 / 357,
        containment: "#container"
    });
}

function GetPosition() {
    var selectorPosition = $("#selector").position(),
        containerSize = {width: $("#container").width(), height: $("#container").height()},
        selectorSize = {width: $("#selector").width(), height: $("#selector").height()};

    $("#cover_aoi").val("[" +
        (selectorPosition.left + (selectorSize.width * 0.26))/containerSize.width + "," +
        (selectorPosition.top + (selectorSize.height * 0.08))/containerSize.height + "," +
        (selectorPosition.left+selectorSize.width - (selectorSize.width * 0.24))/containerSize.width + "," +
        (selectorPosition.top+selectorSize.height - (selectorSize.height * 0.08))/containerSize.height + "]"
    );
}

$(document).ready(function() {
    $("#cover").change(function(){
        PreviewImage();
    });

    $(".form-horizontal").submit(function(e){
        GetPosition();
    });

    if (typeof ($(".cover-image-background img").attr('src')) !== "undefined") {
        ShowImage($(".cover-image-background img").attr('src'));
    }

})