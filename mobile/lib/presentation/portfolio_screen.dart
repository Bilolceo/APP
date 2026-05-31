import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/portfolio_models.dart';
import '../state/app_providers.dart';
import 'widgets/error_banner.dart';
import 'widgets/loading_button.dart';

/// Portfolio boshqaruv ekrani (R11, 20.2).
///
/// Eslatma: ushbu bosqichda yuklash `fayl yo'li` orqali amalga oshiriladi.
class PortfolioScreen extends ConsumerStatefulWidget {
  /// Konstruktor.
  const PortfolioScreen({super.key});

  @override
  ConsumerState<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends ConsumerState<PortfolioScreen> {
  late Future<List<PortfolioItem>> _future;

  final _pathController = TextEditingController();
  final _titleController = TextEditingController();

  bool _isUploading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _pathController.dispose();
    _titleController.dispose();
    super.dispose();
  }

  Future<List<PortfolioItem>> _load() {
    return ref.read(portfolioApiProvider).mine();
  }

  Future<void> _reload() async {
    setState(() {
      _future = _load();
      _errorMessage = null;
    });
    await _future;
  }

  Future<void> _upload() async {
    final path = _pathController.text.trim();
    final title = _titleController.text.trim();

    if (path.isEmpty) {
      setState(() {
        _errorMessage = 'Fayl yo\'lini kiriting';
      });
      return;
    }

    setState(() {
      _isUploading = true;
      _errorMessage = null;
    });

    try {
      await ref.read(portfolioApiProvider).upload(
            filePath: path,
            title: title.isEmpty ? null : title,
          );
      if (!mounted) return;
      _pathController.clear();
      _titleController.clear();
      await _reload();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Portfolio fayli muvaffaqiyatli yuklandi')),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _errorMessage = '$error';
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isUploading = false;
      });
    }
  }

  Future<void> _deleteItem(PortfolioItem item) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Portfolio yozuvini o\'chirish'),
          content: Text('"${item.title}" yozuvini o\'chirmoqchimisiz?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Bekor qilish'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('O\'chirish'),
            ),
          ],
        );
      },
    );

    if (confirm != true) return;

    try {
      await ref.read(portfolioApiProvider).delete(item.id);
      if (!mounted) return;
      await _reload();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Portfolio yozuvi o\'chirildi')),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _errorMessage = '$error';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Portfolio')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<List<PortfolioItem>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return ListView(
                children: const [
                  SizedBox(height: 180),
                  Center(child: CircularProgressIndicator()),
                ],
              );
            }

            final items = snapshot.data ?? const <PortfolioItem>[];

            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Yangi fayl yuklash',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Fayl yo\'lini kiriting (masalan: /storage/.../doc.pdf).',
                        ),
                        const SizedBox(height: 10),
                        ErrorBanner(message: _errorMessage),
                        TextField(
                          controller: _pathController,
                          enabled: !_isUploading,
                          decoration: const InputDecoration(
                            labelText: 'Fayl yo\'li',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.attach_file_outlined),
                          ),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          controller: _titleController,
                          enabled: !_isUploading,
                          decoration: const InputDecoration(
                            labelText: 'Sarlavha (ixtiyoriy)',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.title_outlined),
                          ),
                        ),
                        const SizedBox(height: 12),
                        LoadingButton(
                          label: 'Portfolio ga yuklash',
                          isLoading: _isUploading,
                          onPressed: _upload,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Mening portfolio yozuvlarim',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                if (snapshot.hasError)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Portfolio ro\'yxatini yuklab bo\'lmadi'),
                          const SizedBox(height: 8),
                          Text('${snapshot.error}'),
                        ],
                      ),
                    ),
                  )
                else if (items.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('Hozircha portfolio yozuvlari mavjud emas'),
                    ),
                  )
                else
                  ...items.map(
                    (item) => Card(
                      child: ListTile(
                        leading: const Icon(Icons.description_outlined),
                        title: Text(item.title),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (item.fileType != null)
                              Text('Turi: ${item.fileType}'),
                            if (item.sizeBytes != null)
                              Text('Hajmi: ${_formatBytes(item.sizeBytes!)}'),
                            if (item.createdAt != null)
                              Text('Sana: ${_formatDateTime(item.createdAt!)}'),
                            if (item.fileUrl != null && item.fileUrl!.isNotEmpty)
                              Text(
                                item.fileUrl!,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                          ],
                        ),
                        trailing: IconButton(
                          tooltip: 'O\'chirish',
                          onPressed: () => _deleteItem(item),
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }

  static String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  static String _two(int value) => value.toString().padLeft(2, '0');

  static String _formatDateTime(DateTime date) {
    final y = date.year;
    final m = _two(date.month);
    final d = _two(date.day);
    final hh = _two(date.hour);
    final mm = _two(date.minute);
    return '$y-$m-$d $hh:$mm';
  }
}
