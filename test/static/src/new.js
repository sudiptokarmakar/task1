/** @odoo-module **/

import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

patch(ExportDataDialog.prototype, {

    setup() {
        super.setup();

        // ✅ Add Google Sheets format
        this.availableFormats.push({
            tag: "google_sheets",
            label: _t("Google Sheets"),
            extension: "",
        });

        // ✅ Ensure selectedFormat index is valid
        if (this.state.selectedFormat >= this.availableFormats.length) {
            this.state.selectedFormat = 0;
        }
    },

    async onClickExportButton() {
        const selectedFormat =
            this.availableFormats[this.state.selectedFormat];

        if (!selectedFormat) {
            return;
        }

        if (selectedFormat.tag === "google_sheets") {
            await this.exportToGoogleSheets();
        } else {
            await this.props.download(
                this.state.exportList,
                this.state.isCompatible,
                selectedFormat.tag
            );
        }
    },

    async exportToGoogleSheets() {
        const fields = this.state.exportList.map(f => f.id);

        await rpc("/web/export/google_sheets", {
            model: this.props.root.resModel,
            fields,
            domain: this.props.root.domain || [],
            context: this.props.context || {},
        });
    },
});
