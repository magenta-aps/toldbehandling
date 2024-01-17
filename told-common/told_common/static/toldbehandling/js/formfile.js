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
    const fileInputContainer = $(".file-input");
    fileInputContainer.on("dragenter", function (event) {
        $(this).addClass("dragover");
    });
    fileInputContainer.on("dragover", function (event) {
        event.preventDefault();
        $(this).addClass("dragover");
    });
    fileInputContainer.on("dragleave", function (event) {
        $(this).removeClass("dragover");
    });
    fileInputContainer.on("drop", function (event){
        event.preventDefault();
        $(this).removeClass("dragover");
        const fileInput = $(this).find("input[type=file]");
        const accept = fileInput.attr("accept");
        const acceptList = accept && accept.split(",");
        const dataTransfer = new DataTransfer();

        for (let item of event.originalEvent.dataTransfer.items) {
            if (item.kind === "file") {
                const file = item.getAsFile();
                if (acceptList) {
                    const extension = file.name.includes(".") ? file.name.substring(file.name.lastIndexOf(".")) : null;
                    if (!(acceptList.includes(file.type) || (extension && acceptList.includes(extension)))) {
                        continue;
                    }
                }
                dataTransfer.items.add(file);
                break;
            }
        }

        fileInput.get(0).files = dataTransfer.files;
        fileInput.trigger("change");
    });
});
