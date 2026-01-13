/** @odoo-module **/

import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

// Global flag to ensure format is added only once per session
let googleSheetsFormatAdded = false;

patch(ExportDataDialog.prototype, {

    setup() {
        super.setup();
        this.notification = useService("notification");

        // Add Google Sheets format after component is mounted
        onMounted(() => {
            if (this.availableFormats && !this.availableFormats.some(f => f.tag === "google_sheets")) {
                this.availableFormats.push({
                    tag: "google_sheets",
                    label: _t("Google Sheets"),
                    extension: "",
                });
                console.log("✅ Google Sheets format added. Total:", this.availableFormats.length);
            }
        });
    },

    async onClickExportButton() {
        const selectedFormat = this.availableFormats[this.state.selectedFormat];

        if (!selectedFormat || !selectedFormat.tag) {
            this.notification.add(_t("Invalid format selected"), { type: "danger" });
            return;
        }

        console.log("📤 Export clicked. Format:", selectedFormat.tag);

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
        console.log("🟢 Starting Google Sheets export...");

        try {
            this.notification.add(_t("Exporting to Google Sheets..."), { type: "info" });

            const result = await rpc("/web/export/google_sheets", {
                model: this.props.root.resModel,
                fields: this.state.exportList.map(f => f.name || f.id),
                field_labels: this.state.exportList.map(f => f.label || f.string || f.name),
                domain: this.props.root.domain || [],
                context: this.props.root.context || {},
//                console.log(this.props.root.domain);
//                console.log(this.props.root.context);
            });
            console.log(this.props.root.selection);
            console.log("📊 Export result:", result);

            if (result.success) {
                this.notification.add(
                    _t("✅ Exported %(count)s records to Google Sheets!", { count: result.records_count }),
                    { type: "success" }
                );
                window.open(result.spreadsheet_url, '_blank');
                this.props.close();
            } else {
                this.notification.add(
                    _t("❌ Export failed: %(error)s", { error: result.error }),
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("❌ Export error:", error);
            this.notification.add(
                _t("Export error: %(error)s", { error: error.message }),
                { type: "danger" }
            );
        }
    },
});

console.log("🟢 Google Sheets Export module loaded!");