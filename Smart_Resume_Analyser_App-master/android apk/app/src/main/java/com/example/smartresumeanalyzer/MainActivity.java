package com.example.smartresumeanalyzer;

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.view.View;
import android.webkit.*;
import android.net.http.SslError;
import android.webkit.SslErrorHandler;
import android.widget.ProgressBar;
import androidx.appcompat.app.AppCompatActivity;
import android.widget.Toast;
import android.util.Log;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.graphics.Bitmap;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.graphics.Color;
import androidx.browser.customtabs.CustomTabsIntent;
import androidx.browser.customtabs.CustomTabColorSchemeParams;
import android.os.Message;
import android.view.WindowManager;
import android.os.Handler;
import android.os.Looper;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private ProgressBar progressBar;
    private static final String STREAMLIT_URL = "https://smart-resume-analyzer-4iddq9m3k6hbjvkmsfus8a.streamlit.app/";
    private static final String TAG = "MainActivity";
    private ValueCallback<Uri[]> filePathCallback;
    private static final int FILE_CHOOSER_RESULT_CODE = 1;
    private CustomTabsIntent customTabsIntent;
    private static final long PAGE_LOAD_TIMEOUT = 15000; // 15 seconds timeout
    private boolean isPageLoadTimeout = false;
    private boolean isPageLoading = false;
    private Handler timeoutHandler;
    private boolean isInitialLoad = true;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Enable hardware acceleration
        getWindow().setFlags(
            WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED,
            WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED);
            
        setContentView(R.layout.activity_main);

        // Initialize Chrome Custom Tabs
        CustomTabColorSchemeParams colorSchemeParams = new CustomTabColorSchemeParams.Builder()
            .setToolbarColor(Color.parseColor("#2196F3"))
            .build();
            
        CustomTabsIntent.Builder builder = new CustomTabsIntent.Builder();
        builder.setShowTitle(true);
        builder.setDefaultColorSchemeParams(colorSchemeParams);
        builder.setShareState(CustomTabsIntent.SHARE_STATE_ON);
        customTabsIntent = builder.build();

        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);

        // Initially hide WebView and show progress
        webView.setVisibility(View.INVISIBLE);
        progressBar.setVisibility(View.VISIBLE);

        // Enable hardware acceleration for WebView
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setUseWideViewPort(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setSupportMultipleWindows(true);
        webSettings.setJavaScriptCanOpenWindowsAutomatically(true);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webSettings.setMediaPlaybackRequiresUserGesture(false);
        
        // Modern caching and performance settings
        webSettings.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
        webSettings.setDatabaseEnabled(true);
        webSettings.setDomStorageEnabled(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            webSettings.setOffscreenPreRaster(true);
        }
        
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);
        
        // Clear any existing data
        webView.clearCache(true);
        webView.clearHistory();
        
        // Enable better rendering
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            webSettings.setSafeBrowsingEnabled(false);
        }
        
        // Enable smooth scrolling
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        webView.setHorizontalScrollBarEnabled(false);
        
        // Set modern user agent
        webSettings.setUserAgentString("Mozilla/5.0 (Linux; Android " + Build.VERSION.RELEASE + ") AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36");

        webView.setWebViewClient(new WebViewClient() {
            private int redirectCount = 0;
            private static final int MAX_REDIRECTS = 30; // Increased from 10 to 30
            private long startTime;

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                startTime = System.currentTimeMillis();
                isPageLoading = true;
                isPageLoadTimeout = false;
                
                Log.d(TAG, "Loading URL: " + url);
                
                if (isInitialLoad) {
                    webView.setVisibility(View.INVISIBLE);
                    progressBar.setVisibility(View.VISIBLE);
                }
                
                // Cancel any existing timeout
                if (timeoutHandler != null) {
                    timeoutHandler.removeCallbacksAndMessages(null);
                }
                
                // Set new timeout
                timeoutHandler = new Handler(Looper.getMainLooper());
                timeoutHandler.postDelayed(() -> {
                    if (isPageLoading) {
                        isPageLoadTimeout = true;
                        isPageLoading = false;
                        progressBar.setVisibility(View.GONE);
                        webView.stopLoading();
                        Toast.makeText(MainActivity.this, "Loading is taking longer than expected. Retrying...", Toast.LENGTH_LONG).show();
                        // Clear cache and cookies on timeout
                        webView.clearCache(true);
                        CookieManager.getInstance().removeAllCookies(null);
                        // Reload with cache disabled temporarily
                        webView.getSettings().setCacheMode(WebSettings.LOAD_NO_CACHE);
                        webView.loadUrl(STREAMLIT_URL);
                        // Reset cache mode after a delay
                        new Handler(Looper.getMainLooper()).postDelayed(() -> {
                            webView.getSettings().setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
                        }, 5000);
                    }
                }, PAGE_LOAD_TIMEOUT);
            }

            @Override
            public void onLoadResource(WebView view, String url) {
                super.onLoadResource(view, url);
                Log.d(TAG, "Loading resource: " + url);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                isPageLoading = false;
                long loadTime = System.currentTimeMillis() - startTime;
                Log.d(TAG, "Page load finished. Time: " + loadTime + "ms URL: " + url);
                
                // Cancel timeout handler since page loaded successfully
                if (timeoutHandler != null) {
                    timeoutHandler.removeCallbacksAndMessages(null);
                }

                // Reset redirect count on successful page load
                redirectCount = 0;

                // Handle initial load completion
                if (isInitialLoad) {
                    isInitialLoad = false;
                    // Delay showing WebView slightly to ensure content is rendered
                    new Handler(Looper.getMainLooper()).postDelayed(() -> {
                        progressBar.setVisibility(View.GONE);
                        webView.setVisibility(View.VISIBLE);
                    }, 500); // Increased delay to 500ms
                } else {
                    progressBar.setVisibility(View.GONE);
                    webView.setVisibility(View.VISIBLE);
                }

                // Inject CSS to prevent white flash and ensure content visibility
                String css = "" +
                    "body { opacity: 1 !important; background-color: #ffffff; }" +
                    ".stApp { opacity: 1 !important; display: block !important; }" +
                    ".main { opacity: 1 !important; display: block !important; }";
                view.evaluateJavascript(
                    "(function() {" +
                    "   var style = document.createElement('style');" +
                    "   style.type = 'text/css';" +
                    "   style.innerHTML = '" + css + "';" +
                    "   document.head.appendChild(style);" +
                    "   document.body.style.display = 'block';" +
                    "   document.body.style.visibility = 'visible';" +
                    "   document.body.style.opacity = '1';" +
                    "})();", null
                );
            }

            @Override
            public void onPageCommitVisible(WebView view, String url) {
                // Show WebView as soon as content is available
                webView.setVisibility(View.VISIBLE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                String url = request.getUrl().toString();
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    Log.e(TAG, "Error loading " + url + ": " + error.getDescription());
                }
                
                // Only handle main frame errors
                if (request.isForMainFrame()) {
                    progressBar.setVisibility(View.GONE);
                    if (isInitialLoad) {
                        // On initial load error, retry once with cache cleared
                        isInitialLoad = false;
                        webView.clearCache(true);
                        CookieManager.getInstance().removeAllCookies(null);
                        new Handler(Looper.getMainLooper()).postDelayed(() -> {
                            webView.loadUrl(STREAMLIT_URL);
                        }, 1000);
                    } else {
                        Toast.makeText(MainActivity.this, "Error loading page. Please check your connection.", Toast.LENGTH_SHORT).show();
                    }
                }
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                Log.d(TAG, "URL clicked: " + url);

                // Don't count redirects for resource loading
                if (!request.isForMainFrame()) {
                    return false;
                }

                // Only count redirects for main frame navigation
                if (request.isForMainFrame()) {
                    redirectCount++;
                    Log.d(TAG, "Redirect count: " + redirectCount);
                    
                    if (redirectCount > MAX_REDIRECTS) {
                        Log.e(TAG, "Too many redirects (" + redirectCount + "). Reloading page...");
                        redirectCount = 0;
                        webView.clearCache(true);
                        CookieManager.getInstance().removeAllCookies(null);
                        new Handler(Looper.getMainLooper()).postDelayed(() -> {
                            webView.loadUrl(STREAMLIT_URL);
                        }, 1000);
                        return true;
                    }
                }

                // Handle external links in Custom Tabs
                if (!url.contains("streamlit.app") && !url.contains("streamlit.io")) {
                    try {
                        customTabsIntent.launchUrl(MainActivity.this, Uri.parse(url));
                        return true;
                    } catch (ActivityNotFoundException e) {
                        try {
                            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                            startActivity(intent);
                        } catch (ActivityNotFoundException e2) {
                            Toast.makeText(MainActivity.this, "No app can handle this link", Toast.LENGTH_LONG).show();
                        }
                        return true;
                    }
                }

                // Let WebView handle Streamlit URLs
                return false;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {
                // Handle target="_blank" links
                WebView.HitTestResult result = view.getHitTestResult();
                String data = result.getExtra();
                if (data != null) {
                    try {
                        customTabsIntent.launchUrl(MainActivity.this, Uri.parse(data));
                    } catch (ActivityNotFoundException e) {
                        try {
                            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(data));
                            startActivity(intent);
                        } catch (ActivityNotFoundException e2) {
                            Toast.makeText(MainActivity.this, "No app can handle this link", Toast.LENGTH_LONG).show();
                        }
                    }
                }
                return false;
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePath,
                                           FileChooserParams fileChooserParams) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = filePath;

                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");

                try {
                    startActivityForResult(Intent.createChooser(intent, "Select File"), FILE_CHOOSER_RESULT_CODE);
                } catch (ActivityNotFoundException e) {
                    Toast.makeText(MainActivity.this, "File chooser is not available", Toast.LENGTH_LONG).show();
                    filePathCallback = null;
                    return false;
                }

                return true;
            }
        });

        if (savedInstanceState == null) {
            webView.loadUrl(STREAMLIT_URL);
        } else {
            webView.restoreState(savedInstanceState);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        
        if (requestCode == FILE_CHOOSER_RESULT_CODE) {
            if (filePathCallback == null) return;
            
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK && data != null) {
                String dataString = data.getDataString();
                if (dataString != null) {
                    results = new Uri[]{Uri.parse(dataString)};
                }
            }
            filePathCallback.onReceiveValue(results);
            filePathCallback = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (isPageLoading) {
            // If page is still loading, stop it and show the previous page
            webView.stopLoading();
            isPageLoading = false;
            if (webView.canGoBack()) {
                webView.goBack();
            } else {
                super.onBackPressed();
            }
        } else if (isPageLoadTimeout) {
            // If page timed out, try reloading
            isPageLoadTimeout = false;
            webView.reload();
        } else if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
    }

    @Override
    protected void onDestroy() {
        if (timeoutHandler != null) {
            timeoutHandler.removeCallbacksAndMessages(null);
        }
        webView.destroy();
        super.onDestroy();
    }
}