$(function(){
    const controls = $('.file-input span, .file-input input[type=text]');
    controls.click(function () {
        $("[name="+$(this).data("fileinput")+"]").trigger('click');
    });
    controls.on("keydown", function (event) {
        if (event.originalEvent.code === "Enter") {
            $("[name="+$(this).data("fileinput")+"]").trigger('click');
            event.preventDefault();
        }
    });
    $(".file-input input[type=file]").change(function () {
        $(".file-input [type=text][data-fileinput="+this.name+"]").val(this.value.replace(/C:\\fakepath\\/i, ""));
    });
});
