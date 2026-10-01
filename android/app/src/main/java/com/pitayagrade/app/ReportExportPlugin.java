package com.pitayagrade.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.CancellationSignal;
import android.os.ParcelFileDescriptor;
import android.print.PageRange;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

@CapacitorPlugin(name = "ReportExport")
public class ReportExportPlugin extends Plugin {
    private boolean saving;
    private WebView printView;

    @PluginMethod
    public void saveCsv(PluginCall call) {
        String data = call.getString("data");
        String filename = call.getString("filename");
        if (data == null || filename == null || !filename.matches("[A-Za-z0-9_.-]+\\.csv")) {
            call.reject("Invalid CSV report");
            return;
        }
        if (saving) {
            call.reject("An export is already open");
            return;
        }
        saving = true;
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("text/csv");
        intent.putExtra(Intent.EXTRA_TITLE, filename);
        try {
            startActivityForResult(call, intent, "csvDestination");
        } catch (RuntimeException error) {
            saving = false;
            call.reject("File picker unavailable", error);
        }
    }

    @ActivityCallback
    private void csvDestination(PluginCall call, ActivityResult result) {
        saving = false;
        if (call == null) return;
        if (result.getResultCode() != Activity.RESULT_OK) {
            call.resolve(new JSObject().put("cancelled", true));
            return;
        }
        Intent resultData = result.getData();
        if (resultData == null || resultData.getData() == null || call.getString("data") == null) {
            call.reject("No export destination or report data");
            return;
        }
        execute(() -> {
            try (OutputStream output = getContext().getContentResolver().openOutputStream(resultData.getData(), "wt")) {
                if (output == null) throw new java.io.IOException("Cannot open destination");
                output.write(call.getString("data").getBytes(StandardCharsets.UTF_8));
                output.flush();
            } catch (Exception error) {
                call.reject("Report could not be saved", error);
                return;
            }
            call.resolve(new JSObject().put("cancelled", false));
        });
    }

    @PluginMethod
    public void printHtml(PluginCall call) {
        String html = call.getString("html");
        if (html == null || html.isEmpty()) {
            call.reject("Report is empty");
            return;
        }
        getActivity().runOnUiThread(() -> {
            if (printView != null) {
                call.reject("A print dialog is already open");
                return;
            }
            PrintManager manager = (PrintManager) getActivity().getSystemService(Context.PRINT_SERVICE);
            if (manager == null) {
                call.reject("Printing unavailable");
                return;
            }
            WebView view = new WebView(getActivity());
            printView = view;
            view.getSettings().setJavaScriptEnabled(false);
            view.getSettings().setAllowFileAccess(false);
            view.getSettings().setAllowContentAccess(false);
            view.getSettings().setBlockNetworkLoads(true);
            view.setWebViewClient(new WebViewClient() {
                private boolean started;
                @Override
                public void onPageFinished(WebView webView, String url) {
                    if (started) return;
                    started = true;
                    PrintDocumentAdapter delegate = webView.createPrintDocumentAdapter("PitayaGrade Report");
                    PrintDocumentAdapter adapter = new PrintDocumentAdapter() {
                        @Override public void onStart() { delegate.onStart(); }
                        @Override public void onLayout(PrintAttributes oldAttrs, PrintAttributes newAttrs,
                                CancellationSignal signal, LayoutResultCallback callback, Bundle extras) {
                            delegate.onLayout(oldAttrs, newAttrs, signal, callback, extras);
                        }
                        @Override public void onWrite(PageRange[] pages, ParcelFileDescriptor destination,
                                CancellationSignal signal, WriteResultCallback callback) {
                            delegate.onWrite(pages, destination, signal, callback);
                        }
                        @Override public void onFinish() {
                            delegate.onFinish();
                            releasePrintView(webView);
                        }
                    };
                    try {
                        manager.print("PitayaGrade Report", adapter, new PrintAttributes.Builder().build());
                        call.resolve(); // Dialog opened, not proof of a completed print job.
                    } catch (RuntimeException error) {
                        releasePrintView(webView);
                        call.reject("Printing unavailable", error);
                    }
                }
            });
            view.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null);
        });
    }

    private void releasePrintView(WebView view) {
        if (printView == view) printView = null;
        view.destroy();
    }

    @Override
    protected void handleOnDestroy() {
        if (printView != null) releasePrintView(printView);
    }
}
