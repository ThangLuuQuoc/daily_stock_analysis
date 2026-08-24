import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { BellRing } from 'lucide-react';
import { alertsApi } from '../api/alerts';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { AlertRuleForm } from '../components/alerts/AlertRuleForm';
import {
  AlertRuleList,
  type AlertRuleBusyState,
  type AlertRuleEnabledFilter,
  type AlertTypeFilter,
} from '../components/alerts/AlertRuleList';
import { AlertTriggerHistory } from '../components/alerts/AlertTriggerHistory';
import { ApiErrorAlert, AppPage, Card, EmptyState, InlineAlert, Loading, PageHeader } from '../components/common';
import type {
  AlertNotificationItem,
  AlertRuleCreateRequest,
  AlertRuleItem,
  AlertRuleTestResponse,
  AlertTriggerItem,
  AlertType,
} from '../types/alerts';
import { formatDateTime } from '../utils/format';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { formatUiText, type UiLanguage } from '../i18n/uiText';

const PAGE_SIZE = 20;

const PAGE_TEXT: Record<UiLanguage, {
  documentTitle: string;
  eyebrow: string;
  title: string;
  description: string;
  createSuccessTitle: string;
  close: string;
  testResultTitle: string;
  notificationsTitle: string;
  notificationsSubtitle: string;
  notificationsLoading: string;
  notificationsEmptyTitle: string;
  notificationsEmptyDescription: string;
  colChannel: string;
  colStatus: string;
  colErrorCode: string;
  colLatency: string;
  colTime: string;
  colDiagnostics: string;
  statusLabel: string;
  triggeredLabel: string;
  observedLabel: string;
  yes: string;
  no: string;
  evaluated: string;
  triggered: string;
  degraded: string;
  skipped: string;
  ruleCreated: string;
}> = {
  zh: {
    documentTitle: '告警中心 - DSA',
    eyebrow: 'Alert Center',
    title: '告警中心',
    description: '管理事件告警、日线技术指标、自选股、持仓/账户联动和大盘红绿灯规则，执行一次性测试，并查看后台评估任务记录的触发历史。',
    createSuccessTitle: '创建成功',
    close: '关闭',
    testResultTitle: '测试结果',
    notificationsTitle: '通知尝试记录',
    notificationsSubtitle: '通知结果',
    notificationsLoading: '正在加载通知尝试记录',
    notificationsEmptyTitle: '暂无通知尝试记录',
    notificationsEmptyDescription: '当前没有可展示的通知尝试明细；告警触发仍会按已配置通知渠道发送。',
    colChannel: '渠道',
    colStatus: '状态',
    colErrorCode: '错误码',
    colLatency: '耗时',
    colTime: '时间',
    colDiagnostics: '诊断',
    statusLabel: '状态：',
    triggeredLabel: '触发：',
    observedLabel: '观察值：',
    yes: '是',
    no: '否',
    evaluated: '评估',
    triggered: '触发',
    degraded: '降级',
    skipped: '跳过',
    ruleCreated: '已创建告警规则「{name}」',
  },
  en: {
    documentTitle: 'Alert Center - DSA',
    eyebrow: 'Alert Center',
    title: 'Alert Center',
    description: 'Manage event alerts, daily technical indicators, watchlists, holdings/account linkage and market traffic-light rules, run one-off tests, and review the trigger history recorded by background evaluation tasks.',
    createSuccessTitle: 'Created',
    close: 'Close',
    testResultTitle: 'Test result',
    notificationsTitle: 'Notification attempts',
    notificationsSubtitle: 'Notification results',
    notificationsLoading: 'Loading notification attempts',
    notificationsEmptyTitle: 'No notification attempts yet',
    notificationsEmptyDescription: 'There are no notification attempt details to show; triggered alerts are still sent via the configured channels.',
    colChannel: 'Channel',
    colStatus: 'Status',
    colErrorCode: 'Error code',
    colLatency: 'Latency',
    colTime: 'Time',
    colDiagnostics: 'Diagnostics',
    statusLabel: 'Status: ',
    triggeredLabel: 'Triggered: ',
    observedLabel: 'Observed: ',
    yes: 'Yes',
    no: 'No',
    evaluated: 'Evaluated',
    triggered: 'Triggered',
    degraded: 'Degraded',
    skipped: 'Skipped',
    ruleCreated: 'Alert rule "{name}" created',
  },
  vi: {
    documentTitle: 'Trung tâm cảnh báo - DSA',
    eyebrow: 'Alert Center',
    title: 'Trung tâm cảnh báo',
    description: 'Quản lý cảnh báo sự kiện, chỉ báo kỹ thuật theo ngày, danh sách theo dõi, liên kết danh mục/tài khoản và quy tắc đèn tín hiệu thị trường, chạy kiểm tra một lần và xem lịch sử kích hoạt do tác vụ đánh giá nền ghi lại.',
    createSuccessTitle: 'Tạo thành công',
    close: 'Đóng',
    testResultTitle: 'Kết quả kiểm tra',
    notificationsTitle: 'Nhật ký gửi thông báo',
    notificationsSubtitle: 'Kết quả thông báo',
    notificationsLoading: 'Đang tải nhật ký gửi thông báo',
    notificationsEmptyTitle: 'Chưa có nhật ký gửi thông báo',
    notificationsEmptyDescription: 'Hiện chưa có chi tiết lần gửi thông báo nào; cảnh báo khi kích hoạt vẫn được gửi qua các kênh đã cấu hình.',
    colChannel: 'Kênh',
    colStatus: 'Trạng thái',
    colErrorCode: 'Mã lỗi',
    colLatency: 'Độ trễ',
    colTime: 'Thời gian',
    colDiagnostics: 'Chẩn đoán',
    statusLabel: 'Trạng thái: ',
    triggeredLabel: 'Kích hoạt: ',
    observedLabel: 'Giá trị quan sát: ',
    yes: 'Có',
    no: 'Không',
    evaluated: 'Đã đánh giá',
    triggered: 'Kích hoạt',
    degraded: 'Giảm cấp',
    skipped: 'Bỏ qua',
    ruleCreated: 'Đã tạo quy tắc cảnh báo "{name}"',
  },
};

const NOTIFICATION_CHANNEL_LABELS: Record<UiLanguage, Record<string, string>> = {
  zh: {
    __cooldown__: '业务冷却',
    __cooldown_read_failed__: '冷却读取失败',
    __noise_suppressed__: '通知降噪',
    __no_channel__: '无可用渠道',
    __dispatch__: '通知调度',
    __context__: '会话渠道',
  },
  en: {
    __cooldown__: 'Business cooldown',
    __cooldown_read_failed__: 'Cooldown read failed',
    __noise_suppressed__: 'Noise suppressed',
    __no_channel__: 'No available channel',
    __dispatch__: 'Notification dispatch',
    __context__: 'Session channel',
  },
  vi: {
    __cooldown__: 'Nghỉ nghiệp vụ',
    __cooldown_read_failed__: 'Đọc trạng thái nghỉ thất bại',
    __noise_suppressed__: 'Khử nhiễu thông báo',
    __no_channel__: 'Không có kênh khả dụng',
    __dispatch__: 'Điều phối thông báo',
    __context__: 'Kênh phiên',
  },
};

const NOTIFICATION_STATUS_LABELS: Record<UiLanguage, {
  success: string;
  cooldownActive: string;
  cooldownReadFailed: string;
  noiseSuppressed: string;
  noChannel: string;
  failed: string;
}> = {
  zh: {
    success: '成功',
    cooldownActive: '冷却抑制',
    cooldownReadFailed: '冷却读取失败',
    noiseSuppressed: '降噪抑制',
    noChannel: '无渠道',
    failed: '失败',
  },
  en: {
    success: 'Success',
    cooldownActive: 'Cooldown suppressed',
    cooldownReadFailed: 'Cooldown read failed',
    noiseSuppressed: 'Noise suppressed',
    noChannel: 'No channel',
    failed: 'Failed',
  },
  vi: {
    success: 'Thành công',
    cooldownActive: 'Bị chặn do nghỉ',
    cooldownReadFailed: 'Đọc trạng thái nghỉ thất bại',
    noiseSuppressed: 'Bị chặn do khử nhiễu',
    noChannel: 'Không có kênh',
    failed: 'Thất bại',
  },
};

function enabledFilterToQuery(value: AlertRuleEnabledFilter): boolean | undefined {
  if (value === 'enabled') return true;
  if (value === 'disabled') return false;
  return undefined;
}

function alertTypeFilterToQuery(value: AlertTypeFilter): AlertType | undefined {
  return value === 'all' ? undefined : value;
}

function testVariant(result: AlertRuleTestResponse): 'success' | 'warning' | 'danger' {
  if (result.status === 'evaluation_error') return 'danger';
  return result.triggered ? 'success' : 'warning';
}

function renderTestResultMessage(result: AlertRuleTestResponse, language: UiLanguage): React.ReactNode {
  const targetResults = result.targetResults ?? [];
  const text = PAGE_TEXT[language];
  return (
    <div className="space-y-2">
      <div>
        {result.message}
        {` · ${text.statusLabel}`}
        {result.status}
        {` · ${text.triggeredLabel}`}
        {result.triggered ? text.yes : text.no}
        {` · ${text.observedLabel}`}
        {result.observedValue == null ? '--' : String(result.observedValue)}
      </div>
      {result.evaluatedCount != null && result.evaluatedCount > 1 ? (
        <div className="text-xs">
          {text.evaluated} {result.evaluatedCount} · {text.triggered} {result.triggeredCount ?? 0} · {text.degraded} {result.degradedCount ?? 0} · {text.skipped} {result.skippedCount ?? 0}
        </div>
      ) : null}
      {targetResults.length > 1 ? (
        <div className="grid gap-1 text-xs">
          {targetResults.slice(0, 20).map((item) => (
            <div key={`${item.target}-${item.status}`} className="flex flex-wrap justify-between gap-2">
              <span>{item.displayTarget ?? item.target}</span>
              <span>
                {item.status}
                {item.recordStatus ? ` / ${item.recordStatus}` : ''}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function formatNotificationChannel(channel: string, language: UiLanguage): string {
  return NOTIFICATION_CHANNEL_LABELS[language][channel] ?? channel;
}

function formatNotificationStatus(notification: AlertNotificationItem, language: UiLanguage): string {
  const labels = NOTIFICATION_STATUS_LABELS[language];
  if (notification.success) return labels.success;
  if (notification.errorCode === 'cooldown_active') return labels.cooldownActive;
  if (notification.errorCode === 'cooldown_read_failed') return labels.cooldownReadFailed;
  if (notification.errorCode === 'noise_suppressed') return labels.noiseSuppressed;
  if (notification.errorCode === 'no_channel') return labels.noChannel;
  return labels.failed;
}

const AlertsPage: React.FC = () => {
  const { language } = useUiLanguage();
  const pageText = PAGE_TEXT[language];
  useEffect(() => {
    document.title = pageText.documentTitle;
  }, [pageText.documentTitle]);

  const [rules, setRules] = useState<AlertRuleItem[]>([]);
  const [rulesTotal, setRulesTotal] = useState(0);
  const [rulesPage, setRulesPage] = useState(1);
  const [enabledFilter, setEnabledFilter] = useState<AlertRuleEnabledFilter>('all');
  const [alertTypeFilter, setAlertTypeFilter] = useState<AlertTypeFilter>('all');
  const [rulesLoading, setRulesLoading] = useState(false);
  const [rulesError, setRulesError] = useState<ParsedApiError | null>(null);
  const [rulesLoaded, setRulesLoaded] = useState(false);

  const [triggers, setTriggers] = useState<AlertTriggerItem[]>([]);
  const [triggersLoading, setTriggersLoading] = useState(false);
  const [triggersError, setTriggersError] = useState<ParsedApiError | null>(null);

  const [notifications, setNotifications] = useState<AlertNotificationItem[]>([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [notificationsError, setNotificationsError] = useState<ParsedApiError | null>(null);

  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<ParsedApiError | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);
  const [busyRule, setBusyRule] = useState<AlertRuleBusyState | null>(null);
  const [testResult, setTestResult] = useState<AlertRuleTestResponse | null>(null);
  const rulesRequestIdRef = useRef(0);

  const loadRules = useCallback(async (pageOverride?: number) => {
    const requestId = rulesRequestIdRef.current + 1;
    rulesRequestIdRef.current = requestId;
    const isLatestRequest = () => rulesRequestIdRef.current === requestId;
    const requestedPage = pageOverride ?? rulesPage;
    const baseQuery = {
      enabled: enabledFilterToQuery(enabledFilter),
      alertType: alertTypeFilterToQuery(alertTypeFilter),
      pageSize: PAGE_SIZE,
    };
    setRulesLoading(true);
    try {
      let response = await alertsApi.listRules({ ...baseQuery, page: requestedPage });
      if (!isLatestRequest()) return null;
      const lastPage = Math.max(1, Math.ceil(response.total / PAGE_SIZE));
      if (response.items.length === 0 && response.total > 0 && requestedPage > lastPage) {
        setRulesPage(lastPage);
        response = await alertsApi.listRules({ ...baseQuery, page: lastPage });
        if (!isLatestRequest()) return null;
      } else if (pageOverride !== undefined && pageOverride !== rulesPage) {
        setRulesPage(pageOverride);
      }
      setRules(response.items);
      setRulesTotal(response.total);
      setRulesError(null);
      setRulesLoaded(true);
      return response;
    } catch (error) {
      if (!isLatestRequest()) return null;
      setRulesError(getParsedApiError(error));
      return null;
    } finally {
      if (isLatestRequest()) {
        setRulesLoading(false);
      }
    }
  }, [alertTypeFilter, enabledFilter, rulesPage]);

  const loadTriggers = useCallback(async () => {
    setTriggersLoading(true);
    try {
      const response = await alertsApi.listTriggers({ page: 1, pageSize: PAGE_SIZE });
      setTriggers(response.items);
      setTriggersError(null);
    } catch (error) {
      setTriggersError(getParsedApiError(error));
    } finally {
      setTriggersLoading(false);
    }
  }, []);

  const loadNotifications = useCallback(async () => {
    setNotificationsLoading(true);
    try {
      const response = await alertsApi.listNotifications({ page: 1, pageSize: PAGE_SIZE });
      setNotifications(response.items);
      setNotificationsError(null);
    } catch (error) {
      setNotificationsError(getParsedApiError(error));
    } finally {
      setNotificationsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRules();
  }, [loadRules]);

  useEffect(() => {
    if (!rulesLoaded) return;
    void loadTriggers();
    void loadNotifications();
  }, [loadNotifications, loadTriggers, rulesLoaded]);

  const handleCreateRule = async (payload: AlertRuleCreateRequest) => {
    setCreateLoading(true);
    setCreateError(null);
    setCreateSuccess(null);
    try {
      const created = await alertsApi.createRule(payload);
      setCreateSuccess(formatUiText(pageText.ruleCreated, { name: created.name }));
      await loadRules(1);
      return true;
    } catch (error) {
      setCreateError(getParsedApiError(error));
      return false;
    } finally {
      setCreateLoading(false);
    }
  };

  const handleToggleEnabled = async (rule: AlertRuleItem) => {
    setBusyRule({ id: rule.id, action: 'toggle' });
    try {
      if (rule.enabled) {
        await alertsApi.disableRule(rule.id);
      } else {
        await alertsApi.enableRule(rule.id);
      }
      await loadRules();
    } catch (error) {
      setRulesError(getParsedApiError(error));
    } finally {
      setBusyRule(null);
    }
  };

  const handleDeleteRule = async (rule: AlertRuleItem) => {
    setBusyRule({ id: rule.id, action: 'delete' });
    try {
      await alertsApi.deleteRule(rule.id);
      await loadRules();
    } catch (error) {
      setRulesError(getParsedApiError(error));
    } finally {
      setBusyRule(null);
    }
  };

  const handleTestRule = async (rule: AlertRuleItem) => {
    setBusyRule({ id: rule.id, action: 'test' });
    setTestResult(null);
    try {
      const result = await alertsApi.testRule(rule.id);
      setTestResult(result);
    } catch (error) {
      setRulesError(getParsedApiError(error));
    } finally {
      setBusyRule(null);
    }
  };

  return (
    <AppPage className="space-y-5">
      <PageHeader
        eyebrow={pageText.eyebrow}
        title={pageText.title}
        description={pageText.description}
      />

      {createError ? <ApiErrorAlert error={createError} onDismiss={() => setCreateError(null)} /> : null}
      {createSuccess ? (
        <InlineAlert
          title={pageText.createSuccessTitle}
          message={createSuccess}
          variant="success"
          action={(
            <button type="button" className="text-sm underline" onClick={() => setCreateSuccess(null)}>
              {pageText.close}
            </button>
          )}
        />
      ) : null}
      {rulesError ? <ApiErrorAlert error={rulesError} onDismiss={() => setRulesError(null)} /> : null}

      <div className="grid items-stretch gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <AlertRuleForm onSubmit={handleCreateRule} isSubmitting={createLoading} />
        <div className="flex h-full min-h-0 flex-col gap-4">
          <AlertRuleList
            className="flex h-full min-h-0 flex-col"
            rules={rules}
            total={rulesTotal}
            page={rulesPage}
            pageSize={PAGE_SIZE}
            isLoading={rulesLoading}
            enabledFilter={enabledFilter}
            alertTypeFilter={alertTypeFilter}
            onEnabledFilterChange={(value) => {
              setEnabledFilter(value);
              setRulesPage(1);
            }}
            onAlertTypeFilterChange={(value) => {
              setAlertTypeFilter(value);
              setRulesPage(1);
            }}
            onPageChange={setRulesPage}
            onToggleEnabled={(rule) => void handleToggleEnabled(rule)}
            onDelete={(rule) => void handleDeleteRule(rule)}
            onTest={(rule) => void handleTestRule(rule)}
            busyRule={busyRule}
          />
          {testResult ? (
            <InlineAlert
              title={pageText.testResultTitle}
              variant={testVariant(testResult)}
              message={renderTestResultMessage(testResult, language)}
            />
          ) : null}
        </div>
      </div>

      {triggersError ? <ApiErrorAlert error={triggersError} onDismiss={() => setTriggersError(null)} /> : null}
      <AlertTriggerHistory triggers={triggers} isLoading={triggersLoading} />

      {notificationsError ? <ApiErrorAlert error={notificationsError} onDismiss={() => setNotificationsError(null)} /> : null}
      <Card title={pageText.notificationsTitle} subtitle={pageText.notificationsSubtitle} variant="bordered" padding="md">
        {notificationsLoading ? <Loading label={pageText.notificationsLoading} /> : null}
        {!notificationsLoading && notifications.length === 0 ? (
          <EmptyState
            icon={<BellRing className="h-6 w-6" />}
            title={pageText.notificationsEmptyTitle}
            description={pageText.notificationsEmptyDescription}
          />
        ) : null}
        {!notificationsLoading && notifications.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="border-b border-border/60 text-xs uppercase text-muted-text">
                <tr>
                  <th className="px-3 py-2 font-medium">{pageText.colChannel}</th>
                  <th className="px-3 py-2 font-medium">{pageText.colStatus}</th>
                  <th className="px-3 py-2 font-medium">{pageText.colErrorCode}</th>
                  <th className="px-3 py-2 font-medium">{pageText.colLatency}</th>
                  <th className="px-3 py-2 font-medium">{pageText.colTime}</th>
                  <th className="px-3 py-2 font-medium">{pageText.colDiagnostics}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {notifications.map((notification) => (
                  <tr key={notification.id}>
                    <td className="px-3 py-3">{formatNotificationChannel(notification.channel, language)}</td>
                    <td className="px-3 py-3">{formatNotificationStatus(notification, language)}</td>
                    <td className="px-3 py-3">{notification.errorCode ?? '--'}</td>
                    <td className="px-3 py-3">{notification.latencyMs == null ? '--' : `${notification.latencyMs}ms`}</td>
                    <td className="px-3 py-3">{formatDateTime(notification.createdAt)}</td>
                    <td className="px-3 py-3">{notification.diagnostics ?? '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </AppPage>
  );
};

export default AlertsPage;
