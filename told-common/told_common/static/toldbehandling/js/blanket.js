$(function () {
    // Afsender/modtager opdatering
    // ----------------------------

    const items = [];
    const aktører = window.aktører;
    if (!aktører) {
        return;
    }

    const fillForm = function(i, item) {
        const aktør = aktører[i];
        const fields = aktør["fields"];
        for (let name in fields) {
            let jqElement = $(fields[name]);
            jqElement.val(item[name] || "");
        }
    }

    for (let i = 0; i < aktører.length; i++) {
        const aktør = aktører[i];
        const fields = aktør["fields"];
        const api = aktør["api"];
        const multi_container = $(aktør["multi_container"]);
        const labels = aktør["multi_label"];
        const multi_select = multi_container.find("select");
        items.push([]);

        multi_select.change(function () {
            const id = $(this).val();
            if (id === "") {
                fillForm(i, {});
            } else {
                const item = items[i][id];
                fillForm(i, item);
            }
            updateChangeWarning();
        });

        const updateChoices = function(fieldName, event, callback) {
            const filter = {"kladde": false};
            for (let searchfield of aktør["searchfields"]) {
                const value = $(fields[searchfield]).val();
                if (value !== "") {
                    filter[searchfield] = value;
                }
            }
            if (filter[fieldName]) {
                const warning = multi_container.find(".multiple");
                const hiddenfield = multi_container.find("[type=hidden]");
                $.ajax({
                    "url": api,
                    "data": filter,
                    "success": function (response_data) {
                        const count = response_data["count"];
                        const response_items = response_data["items"];
                        items[i] = {}
                        for (let item of response_items) {
                            items[i][item["id"]] = item;
                        }
                        if (count > 1) {
                            multi_select.empty();
                            multi_select.append('<option value=""></option>');
                            for (let id in items[i]) {
                                const item = items[i][id];
                                let text = [
                                    item["navn"],
                                    item["adresse"],
                                    [item["postnummer"], item["by"]].filter((x) => x !== null && x !== undefined).join(" ")
                                ].filter((x) => x !== null && x !== undefined).join(', ');
                                multi_select.append('<option value="' + id + '">' + text + '</option>');
                            }
                            for (let label in labels) {
                                const element = $(labels[label]);
                                element.toggle(label === fieldName);
                            }
                            warning.show();
                            hiddenfield.hide();
                        } else if (count === 1) {
                            const item = response_items[0];
                            fillForm(i, item);
                            hiddenfield.val(item["id"]);
                            hiddenfield.show();
                            warning.hide();
                            updateChangeWarning();
                        } else {
                            warning.hide();
                            hiddenfield.hide();
                        }
                        if (callback) {
                            callback();
                        }
                    }
                });
            }
        };
        for (let searchfield of aktør["searchfields"]) {
            $(fields[searchfield]).on("change", updateChoices.bind($(fields[searchfield]), searchfield));
        }

        const updateChangeWarning = function () {
            const items_count = Object.keys(items[i]).length;
            let id;
            if (items_count === 0) {
                multi_container.find(".changed").hide();
                return;
            } else if (items_count === 1) {
                id = Object.keys(items[i])[0];
            } else {
                id = multi_select.val();
            }
            let anyChanged = false;
            if (id !== null) {
                const existing = items[i][id];
                if (existing) {
                    for (let fieldname in aktør["fields"]) {
                        const newValue = $(aktør["fields"][fieldname]).val();
                        const oldValue = existing[fieldname] === null ? "" : existing[fieldname].toString();
                        if (newValue !== oldValue) {
                            anyChanged = true;
                            break;
                        }
                    }
                }
            }
            multi_container.find(".changed").toggle(anyChanged);
        };
        for (let fieldname in aktør["fields"]) {
            const field = $(aktør["fields"][fieldname]);
            field.change(updateChangeWarning);
        }
    }
});

$(function () {

    // Vis afgiftssats og beregn afgiftsbeløb
    // --------------------------------------
    const varesatser = JSON.parse($('#varesatser').text());
    let afgiftstabeller;
    if ($('#afgiftstabeller').length) {
        afgiftstabeller = JSON.parse($('#afgiftstabeller').text());
    } else {
        afgiftstabeller = [];
    }
    const konstanter = JSON.parse($('#konstanter').text());
    const tillægsafgift_faktor = konstanter["tillægsafgift_faktor"] || 0;
    const ekspeditionsgebyr = konstanter["ekspeditionsgebyr"] || 0;
    const decimal_fields = ["afgiftssats", "segment_nedre", "segment_øvre"];
    for (key in varesatser) {
        const varesats = varesatser[key];
        for (let fieldname of decimal_fields) {
            if (varesats[fieldname]) {
                varesats[fieldname] = parseFloat(varesats[fieldname]);
            }
        }
    }

    const replace_repeat = function (subject, re, replacement) {
        let old = null;
        while (old !== subject) {
            old = subject;
            subject = subject.replace(re, replacement);
        }
        return subject;
    };

    const get_sub_varesatser = function (varesats) {
        const subs = [];
        const id = varesats["id"];
        for (let kode in varesatser) {
            subsats = varesatser[kode]
            if (subsats["overordnet"] === id) {
                subs.push(subsats);
            }
        }
        return subs;
    }

    const get_afgiftssats_text = function (varesats) {
        const enhed = varesats["enhed"];
        /*if (enhed === "sam") {
            const tekster = [];
            for (let subsats of get_sub_varesatser(varesats)) {
                tekster.push(get_afgiftssats_text(subsats))
            }
            return tekster.join(" + ");
        }*/
        return window.satsTekster[enhed].replace("%f", formatMoney(varesats["afgiftssats"]))
    }

    const formatMoney = function(value) {
        if (typeof(value) !== "number") {
            value = parseFloat(value);
        }
        let intPart = String(Math.floor(value));
        let floatPart = String((value - Math.floor(value)).toPrecision(2));
        intPart = replace_repeat(intPart, /^(-?\d+)(\d\d\d)(\.|,|$)/, '$1.$2$3');  // Starting from the right, prefix groups of 3 digits with a dot
        floatPart = floatPart.substring(2, 4).padEnd(2, "0")  // Get the two first digits of the decimal
        return intPart + "," + floatPart;
    }

    // Vis varekode ved ændring i dropdown
    // -----------------------------------
    const updateVareart = function(subform) {
        if (!subform) {
            subform = $(this);
        }
        if (!(subform instanceof $)) {
            subform = $(subform);
        }
        const vareafgiftssats = subform.find("[name$=vareafgiftssats]");
        const varesats = varesatser[vareafgiftssats.val()];
        if (varesats === undefined) {
            return
        }

        const enhed = varesats["enhed"];
        const varekode = String(varesats["afgiftsgruppenummer"]).padStart(3, "0");
        subform.find("[data-value=varekode]").val(varekode);
        subform.find("[data-value=varekode]").attr("title", varekode);
        subform.find("[data-value=afgiftssats]").val(get_afgiftssats_text(varesats));
        subform.find("[data-value$=mængde]").toggle(enhed in ["kg", "l", "pct"]);
        subform.find("[data-value$=antal]").toggle(enhed in ["ant", "pct"]);
    };

    const container = $("#formset_container");


    const calcSubAfgift = function(varesats, kg_l, antal, beløb) {
        const afgiftssats = varesats["afgiftssats"]
        if (varesats["segment_øvre"]) {
            beløb = Math.min(beløb, varesats["segment_øvre"]);
        }
        if (varesats["segment_nedre"]) {
            beløb = Math.max(0, beløb - varesats["segment_nedre"]);
        }
        switch (varesats["enhed"]) {
            case "ant":
                return antal * afgiftssats;
            case "l":
            case "kg":
                return kg_l * afgiftssats;
            case "pct":
                return beløb * 0.01 * afgiftssats;
            case "sam":
                let afgift = 0
                for (let subsats of get_sub_varesatser(varesats)) {
                    afgift += calcSubAfgift(subsats, kg_l, antal, beløb)
                }
                return afgift;
        }
    }

    const calcAfgift = function (subform) {
        if (!(subform instanceof $)) {
            subform = $(subform);
        }
        const vareafgiftssats = subform.find("[name$=vareafgiftssats]");
        const varesats = varesatser[vareafgiftssats.val()];
        if (varesats === undefined) {
            return
        }

        const afgift = calcSubAfgift(
            varesats,
            parseFloat(subform.find("[name$=mængde]").val()),
            parseFloat(subform.find("[name$=antal]").val()),
            parseFloat(subform.find("[name$=fakturabeløb]").val()),
        );

        subform.find("[data-value=afgiftsbeløb]").val(
            isNaN(afgift) ? "" : formatMoney(afgift)
        );
        subform.data("afgift", isNaN(afgift) ? null : afgift);
        calcAfgiftSum();
    };
    const calcAfgiftSum = function() {
        let totalAfgift = 0;
        let tillægsafgift = 0;
        container.find(".row").each(function () {
            const subform = $(this);
            const vareafgiftssats = subform.find("[name$=vareafgiftssats]");
            const varesats = varesatser[vareafgiftssats.val()];
            if (varesats === undefined) {
                return
            }

            const afgift = subform.data("afgift");
            if (afgift !== null) {
                totalAfgift += afgift;
            }
            if (varesats["har_privat_tillægsafgift_alkohol"]) {
                tillægsafgift += tillægsafgift_faktor * afgift;
            }
        });
        $("[data-value=sum-afgiftsbeløb]").val(formatMoney(totalAfgift));
        $("[data-value=sum-tillægsafgift]").val(formatMoney(tillægsafgift));
        $("[data-value=ekspeditionsgebyr]").val(formatMoney(ekspeditionsgebyr));
        $("[data-value=sum-total]").val(formatMoney(totalAfgift + tillægsafgift + ekspeditionsgebyr));
    };

    // Formset
    // -------
    const formset = container.formset("form", $("#formset_prototype"));
    const subformAdded = function(subform) {
        if (!(subform instanceof $)) {
            subform = $(subform);
        }
        subform.find(".remove-row").click(removeForm.bind(subform, subform));
        subform.find("[name$=vareafgiftssats]").on("change", updateVareart.bind(subform, subform));
        subform.find("input,select").on("change", calcAfgift.bind(subform, subform));
        updateVareart(subform);
        calcAfgift(subform);
        const addButton = subform.find(".add-row");
        addButton.click(addForm);
        subformsUpdated();
    };
    const subformRemoved = function(subform) {
        calcAfgiftSum();
        const rows = container.find(".row");
        rows.each(function (index, element) {
            $(this).find("input[name],select[name]").each(function (){
                this.id = this.id.replace(/-\d+-/, "-"+index+"-");
                this.name = this.name.replace(/-\d+-/, "-"+index+"-");
            });
        });
        subformsUpdated();
    };
    const subformsUpdated = function () {
        const rows = container.find(".row");
        const lastRow = rows.last();
        lastRow.find(".add-row").show();
        if (rows.length === 1) {
            lastRow.find(".remove-row").hide();
        } else {
            rows.find(".remove-row").show();
            rows.not(lastRow).find(".add-row").hide();
        }
    }

    const addForm = function () {
        const newForm = formset.addForm();
        subformAdded(newForm);
    };
    const removeForm = function(subform) {
        formset.removeForm(subform, true);
        subformRemoved(subform);
    };
    container.find(".row").each(function (){subformAdded(this)});

    // Filefield
    // ---------
    const fileUpdate = function() {
        // Validér filstørrelse
        if (this.files.length) {
            const maxsize = this.getAttribute("max_size");
            const filesize = this.files[0].size;
            const associated = $("input[data-fileinput="+this.name+"]");
            if (maxsize && filesize > maxsize) {
                const message = this.getAttribute("data-validity-sizeoverflow")
                this.setCustomValidity(message);
                associated.each(function () {
                    this.setCustomValidity(message);
                })
                associated.addClass("is-invalid");
                associated.attr("title", message)
            } else {
                this.setCustomValidity("");
                associated.each(function () {
                    this.setCustomValidity("");
                })
                associated.removeClass("is-invalid");
                associated.attr("title", "");
            }
        }
    };
    const fileInputs = $("input[type=file]");
    fileInputs.change(fileUpdate);
    fileInputs.each(fileUpdate);


    // TF5: Når indleveringsdato opdateres, brug den rigtige afgiftstabel
    $("[name=indleveringsdato]").on("change", function () {
        const date = Date.parse($(this).val());
        for (let afgiftstabel of afgiftstabeller) {
            if (Date.parse(afgiftstabel["gyldig_fra"]) <= date && (afgiftstabel["gyldig_til"] == null || Date.parse(afgiftstabel["gyldig_til"]) > date)) {
                const varesatser_by_afgiftsgruppenummer = {};
                for (let key in varesatser) {
                    let varesats = varesatser[key];
                    if (varesats["afgiftstabel"] === afgiftstabel["id"]) {
                        varesatser_by_afgiftsgruppenummer[varesats["afgiftsgruppenummer"]] = varesats;
                    }
                }
                $("[name$=vareafgiftssats]").each(function () {
                    const $this = $(this);
                    const currentValue = $this.val();
                    $(this).find("option").not("[value=-1]").remove();
                    for (let key in varesatser_by_afgiftsgruppenummer) {
                        const item = varesatser_by_afgiftsgruppenummer[key];
                        $(this).append($('<option value="' + item["id"] + '">' + item["vareart_da"] + '</option>'));
                    }
                    if (!$this.parents("#formset_prototype").length && currentValue !== "-1") {  // Not the prototype row, and not if nothing is selected
                        const old_sats = varesatser[currentValue];
                        const new_sats = varesatser_by_afgiftsgruppenummer[old_sats["afgiftsgruppenummer"]]
                        $this.val(new_sats["id"]);
                    }
                    const subform = $(this).parents(".row");
                    updateVareart(subform);
                    calcAfgift(subform);
                });
                break;
            }
        }
    });

    $("form").on("input", "[data-value=varekode]", function () {
        $this = $(this);
        const varekode = $this.val();

        // convert varekode zero-padded string to integer
        const varekode_int = parseInt(varekode, 10);
        if (isNaN(varekode_int)) {
            return;
        }

        // Update the entered varekode with leading zeros
        const varekode_str = String(varekode_int).padStart(3, "0")
        $this.val(varekode_str);

        // Update vareafgiftssats select-dropdown
        const vareafgiftssats = $this.parents(".row").find("[name$=vareafgiftssats]");

        let foundVaresats = null;
        for(let key in varesatser) {
            const varesats = varesatser[key];
            if (varekode_int === varesats["afgiftsgruppenummer"]) {
                foundVaresats = varesats;
                break;
            }
        }

        if (foundVaresats) {
            vareafgiftssats.val(foundVaresats["id"]);
            $this.removeClass("is-invalid");
            $this.attr("title", varekode_str);
        } else {
            vareafgiftssats.val(-1);
            $this.addClass("is-invalid");
            $this.attr("title", "Ukendt varekode");
        }
    });
});

$(function () {
    // Custom-fejlbeskeder i klientvalidering
    const validity_checks = ["rangeUnderflow", "rangeOverflow", "patternMismatch"];
    const find = validity_checks.map((check) => "input[data-validity-"+check.toLowerCase()+"]").join(",");
    const updateValidity = function() {
        const valid = this.checkValidity();
        if (!valid) {
            for (let check of validity_checks) {
                if (this.validity[check]) {
                    this.setCustomValidity(
                        this.getAttribute("data-validity-" + check.toLowerCase())
                    );
                    return true;
                }
            }
        }
        this.setCustomValidity("");
        return false;
    }
    $(find).on("input", updateValidity);
    $(find).trigger("input");
});

$(function (){
    const draftField = $("[name=kladde]");

    const setRequired = function(jqField, required) {
        if (required) {
            jqField.attr("required", "required");
        } else {
            jqField.removeAttr("required");
        }
        jqField.each(function () {
            const labels = $("label[for="+$(this).attr("name")+"], label[for="+this.id+"]");
            labels.each(function () {
                const label = $(this);
                let text = label.text();
                // Erstat [0..n] trailing asterisks med asterisk eller ingenting
                text = text.replace(/\**$/, required ? "*":"");
                label.text(text);
            });
        });
    }

    $("[data-required-field]").each(function () {
        const $this = $(this);
        const fieldExpr = $this.data("required-field");  // f.eks. "[name=foobar]"
        // Liste af værdier som gør at vi nu er required
        // Hvis vi ikke er en kladde, og bare ét felt som matcher `fieldExpr` har en af disse værdier, er feltet `this` required
        const values = $this.data("required-values").split(",");
        const updateRequired = function () {
            const fields = $(fieldExpr);
            const fieldValues = new Set();
            fields.each(function () {
                if (document.contains(this)) {
                    // Hent feltets værdi hvis det er i DOM
                    fieldValues.add($(this).val());
                }
            })
            const draft = draftField && draftField.val() && draftField.val().toLowerCase() === "true";
            if (draft) {
                setRequired($this, false);
            } else {
                // Tjek om der er sammenfald mellem values of fieldValues
                let found = false;
                for (let value of values) {
                    if (fieldValues.has(value)) {
                        found = true;
                        break;
                    }
                }
                setRequired($this, found);
            }
        }
        $(fieldExpr).on("change", updateRequired);
        draftField.on("change", updateRequired);
        updateRequired();
        const formset = $("#formset");
        // Revidér når der fjernes en række
        formset.on("subform.post_remove", updateRequired);
        // Tilføj change-listener på felter i tilføjede rækker
        formset.on("subform.post_add", function(event, row) {
            $(row).find(fieldExpr).on("change", updateRequired);
        });
    });

    const required_fields = $("input,select,textarea").filter("[required]").not("[data-required-field]");

    const draftChanged = function () {
        const draft = draftField && draftField.val() && draftField.val().toLowerCase() === "true";
        setRequired(required_fields, !draft);
    };
    draftField.on("change", draftChanged);
    draftChanged();
});

$(function () {
    if ($('#indberetter_data').length) {
        const indberetter_data = JSON.parse($('#indberetter_data').text());
        let $betales_af_select = $("#id_betales_af")

        if (indberetter_data !== null && $betales_af_select.length > 0) {
            let options = $betales_af_select.find("option");
            for (let i = 0; i < options.length; i++) {
                let option = $(options[i]);
                if (option.val() === "indberetter") {
                    option.text(option.text() + ` (CVR: ${indberetter_data["cvr"]})`)
                    break;
                }
            }
        }
    }
})

$("input[readonly]").on("focus", function(){
    this.blur();
});
